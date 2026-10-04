"""Read-only research views over the saved AMPA model and Phase 4 artifacts."""
from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np
from sqlalchemy import select

from app.models import Attempt, MistakeEvent, Prediction, Question
from app.services.ampa_service import _interaction
from app.core.time import utc_isoformat
try:
    from backend.ml.ampa.features import FEATURE_NAMES, RISK_FEATURE_NAMES, MISTAKE_CLASSES
    from backend.ml.ampa.model import MISTIQAMPA
    from backend.ml.ampa.risk import class_risk, softmax
except ModuleNotFoundError:
    from ml.ampa.features import FEATURE_NAMES, RISK_FEATURE_NAMES, MISTAKE_CLASSES
    from ml.ampa.model import MISTIQAMPA
    from ml.ampa.risk import class_risk, softmax

ROOT = Path(__file__).resolve().parents[3]
EXPERIMENTS = ROOT / "experiments"
FEATURE_LABELS = {
    "mistake_frequency": "Mistake Frequency", "mistake_recency": "Mistake Recency",
    "repetition_score": "Repetition Score", "difficulty_sensitivity": "Difficulty Sensitivity",
    "behavior_pressure": "Behavior Pressure", "concept_confusion": "Concept Confusion",
    "learning_stability": "Learning Stability", "instability": "Instability",
    "mistake_momentum": "Mistake Momentum",
}


def _json_safe(value):
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, (np.floating, np.integer)):
        return value.item()
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [_json_safe(v) for v in value]
    return value


def model_details(model):
    params = model.get_parameters()
    config = params["configuration"]
    fitted = bool(model.fitted_)
    return {
        "model_name": "MISTIQ-AMPA", "model_version": params["version"],
        "classes": list(params["classes"]), "features": list(RISK_FEATURE_NAMES),
        "feature_count": len(RISK_FEATURE_NAMES), "class_count": len(params["classes"]),
        "training_status": "trained" if fitted else "not_trained",
        "evaluation_status": "available" if (EXPERIMENTS / "reports" / "comparison.csv").is_file() else "unavailable",
        "weights": _json_safe(params["W"]), "bias": _json_safe(params["b"]),
        "normalization": {"mean": _json_safe(params["feature_mean"]), "scale": _json_safe(params["feature_scale"]),
                          "stability_transform": "instability = 1 - learning_stability"},
        "hyperparameters": _json_safe(config),
        "training_metadata": _json_safe(params["training_metadata"]),
        "feature_definitions": [
            {"name": name, "label": FEATURE_LABELS[name].title(), "symbol": symbol, "description": desc, "range": "engineered features are in [0, 1], except signed momentum in [-1, 1]; standardized scoring values are unbounded", "role": role}
            for name, symbol, desc, role in [
                ("mistake_frequency", "F", "A blend of class-specific error frequency and bounded decayed mistake memory.", "Historical class risk."),
                ("mistake_recency", "R", "Newest matching mistake's exponential age weight.", "Emphasizes recent matching errors."),
                ("repetition_score", "A", "Normalized logarithmic amplification from the count of matching errors.", "Represents repeated occurrences with sublinear growth."),
                ("difficulty_sensitivity", "D", "Hard-minus-easy error-rate vulnerability, scaled to candidate difficulty; fallback when data is sparse.", "Adjusts class risk to difficulty."),
                ("behavior_pressure", "B", "Absolute log ratio of latest response time to prior median, bounded at 1; context may supply a value.", "Captures unusual response-time behavior, not student speed as a trait."),
                ("concept_confusion", "C", "Topic-scoped concept-confusion share when the exact topic or subtopic matches a configured concept pair.", "Adds signal for configured concepts."),
                ("learning_stability", "S", "Accuracy multiplied by a consistency term from the student's relevant history.", "Protective history signal; transformed to instability for scoring."),
                ("mistake_momentum", "MM", "tanh of the difference between recent and prior class-risk window means; zero before enough history.", "Direction of recent class-risk change."),
            ]
        ],
    }


def prediction_trace(session, prediction_id: int, service):
    prediction = session.get(Prediction, prediction_id)
    if prediction is None:
        return None
    if prediction.source_attempt_id is None:
        raise ValueError("Prediction has no source attempt; its historical feature snapshot cannot be reconstructed")
    source = session.get(Attempt, prediction.source_attempt_id)
    question = session.get(Question, prediction.context_question_id) if prediction.context_question_id else None
    if source is None or question is None:
        raise ValueError("Prediction source context is incomplete")
    rows = session.execute(
        select(Attempt, Question, MistakeEvent)
        .join(Question, Attempt.question_id == Question.question_id)
        .outerjoin(MistakeEvent, MistakeEvent.attempt_id == Attempt.attempt_id)
        .where(Attempt.student_id == prediction.student_id)
        .order_by(Attempt.timestamp, Attempt.attempt_id)
    ).all()
    snapshot = (prediction.explanation or {}).get("research_trace_snapshot")
    snapshot_fields = {
        "configuration", "inference_as_of", "feature_mean", "feature_scale",
        "raw_features_by_class", "scoring_features_by_class", "weights", "bias",
        "raw_scores", "shifted_scores", "exponentials", "probabilities",
    }
    exact_snapshot = isinstance(snapshot, dict) and snapshot_fields <= snapshot.keys()
    if exact_snapshot:
        configuration = dict(snapshot["configuration"])
        thresholds = configuration.pop("thresholds", {})
        configuration.update({
            "no_reliable_max": thresholds.get("no_reliable_max", 4),
            "low_confidence_max": thresholds.get("low_max", 14),
            "medium_confidence_max": thresholds.get("medium_max", 29),
            "normal_threshold": thresholds.get("normal_threshold", 30),
        })
        replay_model = MISTIQAMPA(**configuration)
        replay_model.weights_ = np.asarray(snapshot["weights"], dtype=float)
        replay_model.bias_ = np.asarray(snapshot["bias"], dtype=float)
        replay_model.feature_mean_ = np.asarray(snapshot["feature_mean"], dtype=float)
        replay_model.feature_scale_ = np.asarray(snapshot["feature_scale"], dtype=float)
        replay_model.fitted_ = True
        cutoff = _parse_utc(snapshot["inference_as_of"])
        verification_status = "EXACT"
    else:
        # Older predictions did not preserve the original feature cutoff or parameters.
        if service.model is None:
            if not service.model_path.is_file():
                raise ValueError("Saved AMPA model is unavailable")
            service.load_once()
        from copy import deepcopy
        try:
            from backend.ml.ampa.state import StudentStateStore
        except ModuleNotFoundError:
            from ml.ampa.state import StudentStateStore
        replay_model = deepcopy(service.model)
        replay_model.student_state = StudentStateStore()
        cutoff = _parse_utc(prediction.created_at)
        verification_status = "APPROXIMATE"
    replayed = 0
    for attempt, q, mistake in rows:
        if (attempt.timestamp, attempt.attempt_id) > (source.timestamp, source.attempt_id):
            break
        replay_model.update(_interaction(attempt, q, mistake))
        replayed += 1
    context = {"topic": question.topic, "subtopic": question.subtopic,
               "difficulty": question.difficulty, "as_of": utc_isoformat(cutoff)}
    raw = replay_model.extract_student_features(prediction.student_id, context)
    transformed = np.array(raw, copy=True)
    transformed[:, 6] = 1.0 - transformed[:, 6]
    normalized = (transformed - replay_model.feature_mean_) / replay_model.feature_scale_
    scores = class_risk(normalized[None, :, :], replay_model.weights_, replay_model.bias_)[0]
    shifted = scores - np.max(scores)
    exponentials = np.exp(shifted)
    probabilities = softmax(scores)
    winner = int(np.argmax(probabilities))
    contributions = normalized * replay_model.weights_
    winner_rows = [{"feature": RISK_FEATURE_NAMES[i], "label": FEATURE_LABELS[RISK_FEATURE_NAMES[i]],
                    "value": float(normalized[winner, i]), "weight": float(replay_model.weights_[winner, i]),
                    "contribution": float(contributions[winner, i])} for i in range(len(RISK_FEATURE_NAMES))]
    winner_rows.sort(key=lambda row: abs(row["contribution"]), reverse=True)
    output = replay_model.predict_for_student(prediction.student_id, context)
    raw_features = {label: {name: float(raw[c, i]) for i, name in enumerate(FEATURE_NAMES)} for c, label in enumerate(MISTAKE_CLASSES)}
    scoring_features = {label: {name: float(normalized[c, i]) for i, name in enumerate(RISK_FEATURE_NAMES)} for c, label in enumerate(MISTAKE_CLASSES)}
    scores_by_class = {label: float(scores[i]) for i, label in enumerate(MISTAKE_CLASSES)}
    shifted_by_class = {label: float(shifted[i]) for i, label in enumerate(MISTAKE_CLASSES)}
    exponentials_by_class = {label: float(exponentials[i]) for i, label in enumerate(MISTAKE_CLASSES)}
    probabilities_by_class = {label: float(probabilities[i]) for i, label in enumerate(MISTAKE_CLASSES)}
    weights, bias = _json_safe(replay_model.weights_), _json_safe(replay_model.bias_)
    if exact_snapshot:
        expected_raw = np.asarray([
            [snapshot["raw_features_by_class"][label][name] for name in FEATURE_NAMES]
            for label in MISTAKE_CLASSES
        ], dtype=float)
        expected_scoring = np.asarray([
            [snapshot["scoring_features_by_class"][label][name] for name in RISK_FEATURE_NAMES]
            for label in MISTAKE_CLASSES
        ], dtype=float)
        expected_scores = np.asarray([snapshot["raw_scores"][label] for label in MISTAKE_CLASSES], dtype=float)
        expected_shifted = np.asarray([snapshot["shifted_scores"][label] for label in MISTAKE_CLASSES], dtype=float)
        expected_exponentials = np.asarray([snapshot["exponentials"][label] for label in MISTAKE_CLASSES], dtype=float)
        expected_probabilities = np.asarray([snapshot["probabilities"][label] for label in MISTAKE_CLASSES], dtype=float)
        exact_operands = (
            np.allclose(raw, expected_raw, rtol=1e-10, atol=1e-12)
            and np.allclose(normalized, expected_scoring, rtol=1e-10, atol=1e-12)
            and np.allclose(scores, expected_scores, rtol=1e-10, atol=1e-12)
            and np.allclose(shifted, expected_shifted, rtol=1e-10, atol=1e-12)
            and np.allclose(exponentials, expected_exponentials, rtol=1e-10, atol=1e-12)
            and np.allclose(probabilities, expected_probabilities, rtol=1e-10, atol=1e-12)
        )
        matches_stored = (
            exact_operands
            and output["predicted_error"] == prediction.predicted_error
            and abs(output["probability"] - prediction.probability) < 1e-9
            and abs(output["confidence"] - prediction.confidence) < 1e-9
            and abs(output["data_reliability"] - prediction.data_reliability) < 1e-9
            and output["confidence_level"] == prediction.status
        )
        verification_status = "EXACT" if matches_stored else "MISMATCH"
    else:
        matches_stored = None
    winner_class = output["predicted_error"] or prediction.predicted_error
    winner_index = list(MISTAKE_CLASSES).index(winner_class)
    winner_rows = [{"feature": name, "label": FEATURE_LABELS[name],
                    "value": scoring_features[winner_class][name],
                    "weight": weights[winner_index][i],
                    "contribution": scoring_features[winner_class][name] * weights[winner_index][i]}
                   for i, name in enumerate(RISK_FEATURE_NAMES)]
    winner_rows.sort(key=lambda row: abs(row["contribution"]), reverse=True)
    return {
        "prediction_id": prediction.id, "student_id": prediction.student_id,
        "source_attempt_id": source.attempt_id, "context": {"topic": question.topic, "subtopic": question.subtopic, "difficulty": question.difficulty, "as_of": utc_isoformat(cutoff)},
        "model_version": prediction.model_version, "attempt_count": replayed,
        "verification_status": verification_status,
        "raw_features_by_class": raw_features,
        "scoring_features_by_class": scoring_features,
        "classes": list(MISTAKE_CLASSES), "weights": weights, "bias": bias,
        "contributions": winner_rows, "raw_scores": scores_by_class,
        "shifted_scores": shifted_by_class,
        "exponentials": exponentials_by_class,
        "probabilities": probabilities_by_class,
        "prediction": output, "stored_prediction": {"predicted_error": prediction.predicted_error, "probability": prediction.probability,
            "confidence": prediction.confidence, "data_reliability": prediction.data_reliability},
        "replay_matches_stored": matches_stored,
    }


def _parse_utc(value):
    from datetime import datetime, timezone
    parsed = value if isinstance(value, datetime) else datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed.astimezone(timezone.utc)


def evaluation_results():
    path = EXPERIMENTS / "reports" / "comparison.csv"
    if not path.is_file():
        return {"available": False, "source": str(path.relative_to(ROOT)), "results": []}
    with path.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    return {"available": bool(rows), "source": str(path.relative_to(ROOT)), "results": rows}


def _read_json(path):
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None


def ablation_results():
    path = EXPERIMENTS / "ablations" / "ablation_results.json"
    rows = _read_json(path)
    if not rows:
        return {"available": False, "source": str(path.relative_to(ROOT)), "results": []}
    return {"available": True, "source": str(path.relative_to(ROOT)), "results": rows}


def calibration_results(model="mistiq-ampa", seed=42):
    path = EXPERIMENTS / "calibration" / f"{model}_seed_{seed}.json"
    return {"available": path.is_file(), "model": model, "seed": seed,
            "source": str(path.relative_to(ROOT)), "result": _read_json(path)}


def confusion_results(model="mistiq-ampa", seed=42):
    path = EXPERIMENTS / "confusion_matrices" / f"{model}_seed_{seed}.json"
    return {"available": path.is_file(), "model": model, "seed": seed,
            "source": str(path.relative_to(ROOT)), "result": _read_json(path)}


def seed_results():
    path = EXPERIMENTS / "reports" / "seed_robustness.json"
    return {"available": path.is_file(), "source": str(path.relative_to(ROOT)), "results": _read_json(path) or {}}


def learning_curve_results():
    path = EXPERIMENTS / "learning_curves" / "learning_curve.json"
    return {"available": path.is_file(), "source": str(path.relative_to(ROOT)), "results": _read_json(path) or []}


def cold_start_results():
    path = EXPERIMENTS / "results" / "cold_start.json"
    return {"available": path.is_file(), "source": str(path.relative_to(ROOT)), "results": _read_json(path) or []}
