"""Derive AMPA's eight class-specific features from prior history.

Every event is strictly filtered to timestamp < prediction time. Most features are
bounded before model normalization; momentum is signed and normalized features can
be outside the original engineered ranges.
"""

from __future__ import annotations

import math
import statistics
from datetime import datetime, timezone
from typing import Mapping, Sequence

import numpy as np

from .memory import mistake_memory
from .momentum import risk_momentum
from .risk import stability_to_instability

FEATURE_NAMES = (
    "mistake_frequency", "mistake_recency", "repetition_score",
    "difficulty_sensitivity", "behavior_pressure", "concept_confusion",
    "learning_stability", "mistake_momentum",
)
RISK_FEATURE_NAMES = (
    "mistake_frequency", "mistake_recency", "repetition_score",
    "difficulty_sensitivity", "behavior_pressure", "concept_confusion",
    "instability", "mistake_momentum",
)
DEFAULT_CONCEPT_PAIRS = (
    ("Precision", "Recall"), ("Ridge", "Lasso"),
    ("Overfitting", "Underfitting"), ("Stack", "Queue"),
    ("BFS", "DFS"), ("Mean", "Median"),
    ("Classification", "Regression"),
)
MISTAKE_CLASSES = (
    "CONCEPT_CONFUSION", "CALCULATION_ERROR", "PROCEDURE_ERROR", "CARELESS_ERROR",
    "TIME_PRESSURE", "DIFFICULTY_FAILURE", "REPEATED_MISTAKE",
)


def class_feature_matrix(history: Sequence[Mapping], as_of: datetime, context: Mapping | None = None,
                         *, decay_rate=0.08, repetition_alpha=0.5, memory_scale=3.0,
                         momentum_window=5, momentum_scale=0.25,
                         concept_pairs=DEFAULT_CONCEPT_PAIRS) -> np.ndarray:
    """Build one [F,R,A,D,B,C,Instability,MM] row per candidate class."""
    context = context or {}
    cutoff = _utc(as_of)
    prior = [event for event in history if _event_time(event) < cutoff]
    topic = context.get("topic")
    relevant = [event for event in prior if topic is None or _get(event, "topic") == topic]
    all_errors = [event for event in relevant if _error(event) != "CORRECT"]
    difficulty = _finite(context.get("difficulty", 3.0), default=3.0)
    difficulty = min(5.0, max(1.0, difficulty))
    difficulty_sensitivity = _difficulty_sensitivity(relevant, difficulty)
    behavior_pressure = _behavior_pressure(relevant, context)
    stability = _learning_stability(relevant)
    instability = float(stability_to_instability(np.array(stability)))
    rows = []
    for mistake_class in MISTAKE_CLASSES:
        typed = [event for event in relevant if _error(event) == mistake_class]
        frequency = len(typed) / max(1, len(relevant))
        memory, recency, count = mistake_memory(
            relevant, mistake_class, cutoff, decay_rate=decay_rate,
            alpha=repetition_alpha, memory_scale=memory_scale,
        )
        amplification = 1.0 + repetition_alpha * math.log1p(count)
        repetition = (amplification - 1.0) / amplification
        concept = _concept_key(context, concept_pairs)
        if concept and mistake_class == "CONCEPT_CONFUSION":
            confusion_events = [event for event in all_errors if _error(event) == "CONCEPT_CONFUSION"]
            confusion = len(confusion_events) / max(1, len(all_errors))
        elif topic is None and mistake_class == "CONCEPT_CONFUSION":
            confusion = sum(_error(event) == "CONCEPT_CONFUSION" for event in all_errors) / max(1, len(all_errors))
        else:
            confusion = 0.0
        history_risk = _class_risk_history(prior, mistake_class, topic)
        momentum, _low_information = risk_momentum(history_risk, window=momentum_window, scale=momentum_scale)
        # Memory is deliberately computed and folded into the frequency signal so
        # occurrence, exponential recency, and repetition all influence class risk.
        frequency = 0.5 * frequency + 0.5 * memory
        rows.append((frequency, recency, repetition, difficulty_sensitivity,
                     behavior_pressure, confusion, stability, momentum))
    return np.asarray(rows, dtype=float)


def _difficulty_sensitivity(history, candidate_difficulty):
    if not history:
        return 0.0
    hard = [event for event in history if _difficulty(event) >= 4]
    easy = [event for event in history if _difficulty(event) <= 2]
    if not hard or not easy:
        return min(1.0, max(0.0, (candidate_difficulty - 1.0) / 4.0 * 0.25))
    hard_rate = sum(_error(event) != "CORRECT" for event in hard) / len(hard)
    easy_rate = sum(_error(event) != "CORRECT" for event in easy) / len(easy)
    vulnerability = min(1.0, max(0.0, hard_rate - easy_rate))
    return vulnerability * ((candidate_difficulty - 1.0) / 4.0)


def _behavior_pressure(history, context):
    supplied = context.get("behavior_pressure")
    if supplied is not None:
        return min(1.0, max(0.0, _finite(supplied)))
    response_times = [_finite(_get(event, "response_time"), default=0.0)
                      for event in history if _get(event, "response_time") is not None]
    response_times = [value for value in response_times if value > 0]
    if len(response_times) < 2:
        return 0.0
    baseline = statistics.median(response_times[:-1])
    if baseline <= 0:
        return 0.0
    return min(1.0, abs(math.log(response_times[-1] / baseline)) / math.log(4.0))


def _learning_stability(history):
    correct_count = sum(_error(event) == "CORRECT" for event in history)
    return learning_stability_from_counts(correct_count, len(history))


def learning_stability_from_counts(correct_count: int, total_count: int) -> float:
    """Evaluate the existing stability feature from sufficient statistics."""
    if total_count <= 0:
        return 0.0
    accuracy = correct_count / total_count
    consistency = 1.0 - min(1.0, 2.0 * math.sqrt(accuracy * (1.0 - accuracy)))
    return min(1.0, max(0.0, accuracy * consistency))


def _class_risk_history(history, target, topic):
    if not history:
        return []
    # One binary class-risk observation at each historical interaction.
    return [float(_error(event) == target and (topic is None or _get(event, "topic") == topic))
            for event in history]


def _concept_key(context, pairs):
    """Use the pair-matching concept label from topic or subtopic consistently."""
    for value in (_get(context, "topic"), _get(context, "subtopic")):
        if value and any(str(value).casefold() == str(member).casefold()
                         for pair in pairs for member in pair):
            return str(value)
    return None


def _difficulty(event):
    return _finite(_get(event, "difficulty"), default=3.0)


def _error(event):
    error = _get(event, "error_type")
    if error is not None:
        return str(getattr(error, "value", error))
    correct = _get(event, "correct")
    return "CORRECT" if correct is True or str(correct).lower() in {"true", "1"} else "CARELESS_ERROR"


def _event_time(event):
    value = _get(event, "_parsed_timestamp", _get(event, "timestamp"))
    return _utc(value if isinstance(value, datetime) else datetime.fromisoformat(str(value).replace("Z", "+00:00")))


def _utc(value):
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def _get(row, key, default=None):
    return row.get(key, default) if isinstance(row, Mapping) else getattr(row, key, default)


def _finite(value, default=0.0):
    try:
        result = float(value)
        return result if math.isfinite(result) else default
    except (TypeError, ValueError):
        return default
