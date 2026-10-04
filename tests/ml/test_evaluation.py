from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pytest

from backend.ml.ampa import MISTIQAMPA
from backend.ml.ampa.features import MISTAKE_CLASSES
from backend.ml.baselines import (DecisionTreeBaseline, KNNBaseline, LogisticRegressionBaseline,
                                  MajorityBaseline, RandomForestBaseline)
from backend.ml.evaluation.ablation import apply_ablation
from backend.ml.evaluation.metrics import evaluate_predictions, expected_calibration_error
from backend.ml.evaluation.results import ExperimentResult, validate_result
from backend.ml.evaluation.splitting import (assert_temporal_order, build_next_mistake_examples,
                                              chronological_split)
from backend.ml.evaluation.runner import _cold_start_evaluation


def _small_raw_data():
    start = datetime(2025, 1, 1, tzinfo=timezone.utc)
    questions, attempts, events = [], [], []
    error_types = ["CORRECT", "CONCEPT_CONFUSION", "CORRECT", "CALCULATION_ERROR",
                   "CORRECT", "PROCEDURE_ERROR", "CORRECT", "CARELESS_ERROR",
                   "CORRECT", "TIME_PRESSURE", "DIFFICULTY_FAILURE", "REPEATED_MISTAKE"]
    for index, error in enumerate(error_types):
        question_id, attempt_id = index + 1, index + 1
        questions.append({"question_id": question_id, "topic": "Precision", "subtopic": "basics",
                          "difficulty": 2 + index % 3, "correct_option": "A"})
        attempts.append({"attempt_id": attempt_id, "student_id": 1, "question_id": question_id,
                         "selected_option": "A" if error == "CORRECT" else "B",
                         "correct": error == "CORRECT", "response_time": 30 + index,
                         "timestamp": (start + timedelta(days=index)).isoformat().replace("+00:00", "Z"),
                         "attempt_number": 1})
        events.append({"mistake_event_id": index + 1, "student_id": 1, "attempt_id": attempt_id,
                       "error_type": error, "topic": "Precision", "subtopic": "basics",
                       "timestamp": attempts[-1]["timestamp"]})
    return questions, attempts, events


def test_chronological_split_is_ordered_and_configurable():
    examples = [{"timestamp": datetime(2025, 1, 1, tzinfo=timezone.utc) + timedelta(days=i),
                 "attempt_id": i + 1} for i in range(20)]
    splits = chronological_split(examples, 0.6, 0.2, 0.2)
    assert [len(splits[key]) for key in ("train", "validation", "test")] == [12, 4, 4]
    assert_temporal_order(splits)


def test_next_mistake_features_exclude_target_and_future_events():
    questions, attempts, events = _small_raw_data()
    examples = build_next_mistake_examples(questions, attempts, events)
    changed = deepcopy(events)
    changed[-1]["error_type"] = "CONCEPT_CONFUSION"
    changed_examples = build_next_mistake_examples(questions, attempts, changed)
    assert len(examples) == len(changed_examples)
    assert np.array_equal(examples[0]["features"], changed_examples[0]["features"])
    assert examples[0]["prior_count"] == 1
    assert examples[0]["target"] == "CONCEPT_CONFUSION"
    # The target event itself is not among the history used to form its features.
    assert all(event["attempt_id"] != examples[0]["attempt_id"] for event in examples[0]["prior_history"])


def test_training_concept_confusion_uses_configured_subtopic_pair():
    questions = [
        {"question_id": 1, "topic": "Machine Learning", "subtopic": "Precision", "difficulty": 3},
        {"question_id": 2, "topic": "Machine Learning", "subtopic": "Recall", "difficulty": 3},
    ]
    attempts = [
        {"attempt_id": 1, "student_id": 1, "question_id": 1, "correct": False,
         "response_time": 30, "timestamp": "2025-01-01T00:00:00Z"},
        {"attempt_id": 2, "student_id": 1, "question_id": 2, "correct": False,
         "response_time": 30, "timestamp": "2025-01-02T00:00:00Z"},
    ]
    events = [
        {"attempt_id": 1, "error_type": "CONCEPT_CONFUSION"},
        {"attempt_id": 2, "error_type": "CALCULATION_ERROR"},
    ]

    examples = build_next_mistake_examples(questions, attempts, events)

    assert examples[1]["features"][0, 5] == 1.0


@pytest.mark.parametrize("baseline", [MajorityBaseline, LogisticRegressionBaseline,
                                       DecisionTreeBaseline, RandomForestBaseline, KNNBaseline])
def test_baselines_fit_and_align_probabilities(baseline):
    X = np.arange(96, dtype=float).reshape(12, 8)
    y = np.asarray([MISTAKE_CLASSES[index % 3] for index in range(len(X))])
    model = baseline()
    model.fit(X, y)
    probabilities = model.predict_proba(X[:3])
    assert probabilities.shape == (3, len(MISTAKE_CLASSES))
    assert np.allclose(probabilities.sum(axis=1), 1.0)
    assert set(model.predict(X[:3])).issubset(set(MISTAKE_CLASSES))


def test_ampa_and_baseline_share_split_examples_and_ablation_removes_pretraining_signal():
    rng = np.random.default_rng(2)
    X = rng.random((15, len(MISTAKE_CLASSES), 8))
    y = np.asarray([MISTAKE_CLASSES[index % len(MISTAKE_CLASSES)] for index in range(15)])
    flattened = X.reshape(len(X), -1)
    assert flattened.shape == (len(X), len(MISTAKE_CLASSES) * 8)
    ablated = apply_ablation(X, "concept_confusion")
    assert np.all(ablated[..., 5] == 0)
    assert np.any(X[..., 5] != 0)
    model = MISTIQAMPA(epochs=5).fit(ablated, y)
    assert model.feature_mean_[5] == 0
    assert model.predict_proba(ablated[:2]).shape == (2, len(MISTAKE_CLASSES))


def test_metrics_confusion_and_calibration_are_bounded():
    labels = MISTAKE_CLASSES
    y = [labels[0], labels[1], labels[0]]
    p = np.zeros((3, len(labels)))
    p[0, 0] = 0.7; p[0, 1] = 0.2; p[0, 2:] = 0.1 / (len(labels)-2)
    p[1, 1] = 0.6; p[1, 0] = 0.3; p[1, 2:] = 0.1 / (len(labels)-2)
    p[2, 1] = 0.6; p[2, 0] = 0.3; p[2, 2:] = 0.1 / (len(labels)-2)
    result = evaluate_predictions(y, p, labels, calibration_bins=5)
    assert result["confusion_matrix"].shape == (len(labels), len(labels))
    for metric in ("accuracy", "macro_precision", "macro_recall", "macro_f1", "weighted_f1",
                   "top2_accuracy", "top3_accuracy", "ece"):
        assert 0 <= result[metric] <= 1
    assert 0 <= result["brier_score"] <= 2
    ece, bins = expected_calibration_error(y, p, labels, bins=5)
    assert 0 <= ece <= 1 and len(bins) == 5


def test_result_schema_and_seed_reproducibility():
    data = {"experiment_id": "test", "model_name": "MISTIQ-AMPA", "model_version": "1",
            "seed": 3, "feature_set": "all", "train_size": 10, "validation_size": 2,
            "test_size": 2, "accuracy": .5, "macro_precision": .5, "macro_recall": .5,
            "macro_f1": .5, "weighted_f1": .5, "log_loss": 1.0, "top2_accuracy": .8,
            "top3_accuracy": .9, "brier_score": .4, "ece": .2,
            "timestamp": "2025-01-01T00:00:00Z"}
    assert validate_result(data) is data
    with pytest.raises(ValueError):
        validate_result({**data, "accuracy": 1.1})
    rng = np.random.default_rng(5); X = rng.random((20, 8)); y = [MISTAKE_CLASSES[i % 3] for i in range(20)]
    first = MISTIQAMPA(seed=8, epochs=8).fit(X, y)
    second = MISTIQAMPA(seed=8, epochs=8).fit(X, y)
    assert np.allclose(first.predict_proba(X), second.predict_proba(X))


def test_cold_start_policy_does_not_score_zero_to_four_attempts():
    model = MISTIQAMPA(epochs=2).fit(np.zeros((7, 8)), MISTAKE_CLASSES)
    test = [{"prior_count": count, "features": np.zeros((7, 8))} for count in range(35)]
    labels = [MISTAKE_CLASSES[index % len(MISTAKE_CLASSES)] for index in range(len(test))]
    rows = _cold_start_evaluation(model, test, labels, 5, 1)
    assert rows[0]["status"] == "NO_RELIABLE_PREDICTION"
    assert rows[0]["scored_count"] == 0
    assert [row["confidence_policy"] for row in rows] == [
        "NO_RELIABLE_PREDICTION", "LOW_CONFIDENCE", "MEDIUM_CONFIDENCE", "NORMAL_OPERATION"]
