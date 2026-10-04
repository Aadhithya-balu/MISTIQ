"""Reproducible temporal evaluation for AMPA and standard baselines."""

from __future__ import annotations

import csv
import json
import statistics
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import sklearn

from ..ampa import MISTIQAMPA
from ..ampa.features import DEFAULT_CONCEPT_PAIRS, MISTAKE_CLASSES, class_feature_matrix
from ..baselines import (DecisionTreeBaseline, KNNBaseline, LogisticRegressionBaseline,
                         MajorityBaseline, RandomForestBaseline)
from .ablation import ABLATIONS, apply_ablation
from .comparison import comparison_csv, comparison_markdown, write_ablation_report
from .metrics import confusion_rows, evaluate_predictions
from .results import ExperimentResult, save_results
from .splitting import assert_temporal_order, build_next_mistake_examples, chronological_split

BASELINES = (MajorityBaseline, LogisticRegressionBaseline, DecisionTreeBaseline,
             RandomForestBaseline, KNNBaseline)
METRIC_KEYS = ("accuracy", "macro_precision", "macro_recall", "macro_f1", "weighted_f1",
               "log_loss", "top2_accuracy", "top3_accuracy", "brier_score", "ece")


def run_evaluation(*, dataset, output, seeds=(42,), epochs=100, run_ablation=True,
                   run_baselines=True, run_cold_start=True, run_learning_curve=True,
                   train_ratio=0.70, validation_ratio=0.15, test_ratio=0.15,
                   calibration_bins=10, learning_curve_steps=(5, 10, 15, 20, 30, 50)):
    output = Path(output)
    for folder in ("results", "confusion_matrices", "calibration", "ablations",
                   "learning_curves", "reports"):
        (output / folder).mkdir(parents=True, exist_ok=True)
    questions, attempts, mistake_events = _load_csv_dataset(dataset)
    examples = build_next_mistake_examples(questions, attempts, mistake_events)
    splits = chronological_split(examples, train_ratio, validation_ratio, test_ratio)
    assert_temporal_order(splits)
    train, validation, test = (splits[name] for name in ("train", "validation", "test"))
    if not train or not validation or not test:
        raise ValueError("chronological split produced an empty partition")
    y_train = [row["target"] for row in train]
    y_validation = [row["target"] for row in validation]
    y_test = [row["target"] for row in test]
    X_train = np.asarray([row["features"] for row in train])
    X_validation = np.asarray([row["features"] for row in validation])
    X_test = np.asarray([row["features"] for row in test])
    seed_results, ablation_results, cold_results, curve_results = [], [], [], []

    for seed in seeds:
        ampa = MISTIQAMPA(seed=seed, epochs=epochs).fit(X_train, y_train)
        result, validation_metrics, test_metrics, test_probabilities = _evaluate_model(
            ampa, "MISTIQ-AMPA", X_validation, y_validation, X_test, y_test,
            seed, train, validation, test, calibration_bins, "all_features", "ampa-1.0",
        )
        seed_results.append(result)
        _save_diagnostics(output, "MISTIQ-AMPA", seed, test_metrics, test_probabilities, y_test)
        _save_validation(output, "MISTIQ-AMPA", seed, validation_metrics)

        if run_baselines:
            train_flat = X_train.reshape(len(X_train), -1)
            validation_flat = X_validation.reshape(len(X_validation), -1)
            test_flat = X_test.reshape(len(X_test), -1)
            for baseline_type in BASELINES:
                baseline = baseline_type(seed=seed) if baseline_type is not KNNBaseline else baseline_type()
                baseline.fit(train_flat, y_train)
                row, val_metrics, metrics, probabilities = _evaluate_model(
                    baseline, baseline.model_name, validation_flat, y_validation,
                    test_flat, y_test, seed, train, validation, test,
                    calibration_bins, "all_features_flattened_candidate_rows",
                    f"scikit-learn-{sklearn.__version__}",
                    baseline_name=baseline.model_name,
                )
                seed_results.append(row)
                _save_diagnostics(output, baseline.model_name, seed, metrics, probabilities, y_test)
                _save_validation(output, baseline.model_name, seed, val_metrics)

        if run_ablation:
            for removed in ABLATIONS[1:]:
                ablated = MISTIQAMPA(seed=seed, epochs=epochs)
                # Mask before fit: the removed signal cannot affect learned weights.
                ablated.fit(apply_ablation(X_train, removed), y_train)
                row, _, metrics, probabilities = _evaluate_model(
                    ablated, f"MISTIQ-AMPA without {removed}",
                    apply_ablation(X_validation, removed), y_validation,
                    apply_ablation(X_test, removed), y_test, seed, train, validation, test,
                    calibration_bins, f"without:{removed}", "ampa-1.0", removed_feature=removed,
                )
                ablation_results.append(row)
                _save_diagnostics(output, f"AMPA_without_{removed}", seed, metrics, probabilities, y_test)

        if run_cold_start:
            cold_results.extend(_cold_start_evaluation(ampa, test, y_test, calibration_bins, seed))
        if run_learning_curve:
            curve_results.extend(_learning_curve_evaluation(ampa, test, y_test, calibration_bins,
                                                           seed, learning_curve_steps))

    save_results(seed_results, output / "results" / "model_results.json", output / "results" / "model_results.csv")
    if ablation_results:
        save_results(ablation_results, output / "ablations" / "ablation_results.json",
                     output / "ablations" / "ablation_results.csv")
        full_ampa_rows = [row for row in seed_results if row.model_name == "MISTIQ-AMPA"]
        write_ablation_report(full_ampa_rows + ablation_results,
                              output / "reports" / "ablation_report.md")
    _save_seed_robustness(seed_results, output / "reports")
    _save_comparison(seed_results, output / "reports")
    if cold_results:
        _write_json(output / "results" / "cold_start.json", cold_results)
    if curve_results:
        _write_json(output / "learning_curves" / "learning_curve.json", curve_results)
        _write_csv(output / "learning_curves" / "learning_curve.csv", curve_results)
    run_summary = {
        "experiment_id": f"mistiq-phase4-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        "seed_list": list(seeds), "dataset": str(dataset), "epochs": epochs,
        "split_sizes": {"train": len(train), "validation": len(validation), "test": len(test)},
        "target": "next non-CORRECT mistake category; feature history strictly precedes target timestamp",
        "results_count": len(seed_results), "ablations_count": len(ablation_results),
    }
    _write_json(output / "reports" / "run_summary.json", run_summary)
    return run_summary


def _evaluate_model(model, name, X_validation, y_validation, X_test, y_test, seed,
                    train, validation, test, bins, feature_set, version, removed_feature=None,
                    baseline_name=None):
    validation_probabilities = model.predict_proba(X_validation)
    test_probabilities = model.predict_proba(X_test)
    validation_metrics = evaluate_predictions(y_validation, validation_probabilities, MISTAKE_CLASSES,
                                              calibration_bins=bins)
    test_metrics = evaluate_predictions(y_test, test_probabilities, MISTAKE_CLASSES,
                                        calibration_bins=bins)
    result = ExperimentResult(
        experiment_id=f"phase4-{name.lower().replace(' ', '-')}-seed-{seed}",
        model_name=name, model_version=version, seed=seed, feature_set=feature_set,
        train_size=len(train), validation_size=len(validation), test_size=len(test),
        **{key: test_metrics[key] for key in METRIC_KEYS},
        removed_feature=removed_feature, baseline_name=baseline_name,
    )
    return result, validation_metrics, test_metrics, test_probabilities


def _cold_start_evaluation(model, test, y_test, bins, seed):
    buckets = (("0-4", 0, 4, "NO_RELIABLE_PREDICTION"),
               ("5-14", 5, 14, "LOW_CONFIDENCE"),
               ("15-29", 15, 29, "MEDIUM_CONFIDENCE"),
               ("30+", 30, None, "NORMAL_OPERATION"))
    outputs = []
    for name, low, high, policy in buckets:
        indices = [i for i, row in enumerate(test)
                   if row["prior_count"] >= low and (high is None or row["prior_count"] <= high)]
        if low < 5:
            outputs.append({"seed": seed, "history_bucket": name, "confidence_policy": policy,
                            "sample_count": len(indices), "scored_count": 0,
                            "status": "NO_RELIABLE_PREDICTION", "metrics": None})
            continue
        if indices:
            probs = model.predict_proba(np.asarray([test[index]["features"] for index in indices]))
            metrics = _serial_metrics(evaluate_predictions([y_test[i] for i in indices], probs,
                                                            MISTAKE_CLASSES, calibration_bins=bins))
        else:
            probs, metrics = None, None
        outputs.append({"seed": seed, "history_bucket": name, "confidence_policy": policy,
                        "sample_count": len(indices), "scored_count": len(indices),
                        "status": "scored" if indices else "no_test_examples", "metrics": metrics})
    return outputs


def _learning_curve_evaluation(model, test, y_test, bins, seed, steps):
    rows = []
    for required in steps:
        indices = [index for index, row in enumerate(test) if row["prior_count"] >= required]
        if not indices:
            rows.append({"seed": seed, "history_attempts": required, "sample_count": 0, "metrics": None})
            continue
        feature_rows = []
        for index in indices:
            example = test[index]
            prior = example["prior_history"][-required:]
            feature_rows.append(class_feature_matrix(prior, example["timestamp"], example["context"],
                                                    concept_pairs=model.concept_pairs or DEFAULT_CONCEPT_PAIRS,
                                                    decay_rate=model.decay_rate,
                                                    repetition_alpha=model.repetition_alpha,
                                                    memory_scale=model.memory_scale,
                                                    momentum_window=model.momentum_window,
                                                    momentum_scale=model.momentum_scale))
        probabilities = model.predict_proba(np.asarray(feature_rows))
        metrics = evaluate_predictions([y_test[i] for i in indices], probabilities,
                                       MISTAKE_CLASSES, calibration_bins=bins)
        rows.append({"seed": seed, "history_attempts": required, "sample_count": len(indices),
                     "metrics": _serial_metrics(metrics)})
    return rows


def _save_diagnostics(output, model_name, seed, metrics, probabilities, y_true):
    safe = model_name.lower().replace(" ", "_")
    path = output / "confusion_matrices" / f"{safe}_seed_{seed}"
    matrix = metrics["confusion_matrix"]
    _write_json(path.with_suffix(".json"), {"labels": MISTAKE_CLASSES, "matrix": matrix.tolist()})
    _write_csv(path.with_suffix(".csv"), confusion_rows(matrix, MISTAKE_CLASSES))
    _write_json(output / "calibration" / f"{safe}_seed_{seed}.json",
                {"brier_score": metrics["brier_score"], "ece": metrics["ece"],
                 "bins": metrics["calibration"], "interpretation": "measured; softmax normalization alone is not calibration"})
    _write_json(output / "results" / f"{safe}_seed_{seed}_per_class.json", metrics["per_class"])


def _save_validation(output, model_name, seed, metrics):
    safe = model_name.lower().replace(" ", "_")
    _write_json(output / "results" / f"{safe}_seed_{seed}_validation.json", _serial_metrics(metrics))


def _save_seed_robustness(rows, reports_dir):
    groups = defaultdict(list)
    for row in rows:
        groups[row.model_name].append(row)
    summary = {}
    for name, values in groups.items():
        summary[name] = {}
        for metric in METRIC_KEYS:
            numbers = [getattr(row, metric) for row in values]
            summary[name][metric] = {"mean": statistics.mean(numbers),
                                     "std": statistics.stdev(numbers) if len(numbers) > 1 else 0.0,
                                     "min": min(numbers), "max": max(numbers), "seeds": len(numbers)}
    _write_json(reports_dir / "seed_robustness.json", summary)


def _save_comparison(rows, reports_dir):
    grouped = defaultdict(list)
    for row in rows:
        grouped[row.model_name].append(row)
    aggregates = []
    for name, values in grouped.items():
        aggregate = {"model_name": name, "seed": "mean"}
        for metric in METRIC_KEYS:
            aggregate[metric] = statistics.mean(getattr(row, metric) for row in values)
        aggregates.append(aggregate)
    comparison_markdown(aggregates, reports_dir / "comparison.md")
    comparison_csv(aggregates, reports_dir / "comparison.csv")


def _serial_metrics(metrics):
    return {key: value for key, value in metrics.items()
            if key not in {"confusion_matrix", "calibration"}}


def _load_csv_dataset(directory):
    directory = Path(directory)
    tables = []
    for name in ("questions", "attempts", "mistake_events"):
        with (directory / f"{name}.csv").open(newline="", encoding="utf-8") as stream:
            tables.append(list(csv.DictReader(stream)))
    return tuple(tables)


def _write_json(path, data):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(data, indent=2, default=_json_default) + "\n", encoding="utf-8")


def _write_csv(path, rows):
    if not rows:
        return
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with Path(path).open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)


def _json_default(value):
    if isinstance(value, (np.integer, np.floating)):
        return value.item()
    if isinstance(value, np.ndarray):
        return value.tolist()
    if hasattr(value, "isoformat"):
        return value.isoformat()
    raise TypeError(f"not JSON serializable: {type(value).__name__}")
