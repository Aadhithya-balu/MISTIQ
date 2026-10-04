"""Chronological next-mistake target construction and temporal splitting."""

from datetime import datetime
from ..ampa.features import DEFAULT_CONCEPT_PAIRS, MISTAKE_CLASSES, class_feature_matrix


def build_next_mistake_examples(questions, attempts, mistake_events, *, ampa_config=None):
    """Build target rows from each mistake; each feature row sees only time < target.

    Correct attempts remain in history, while only a subsequent non-CORRECT event
    becomes the supervised next-mistake label.
    """
    question_map = {str(row["question_id"]): row for row in questions}
    event_map = {str(row["attempt_id"]): row for row in mistake_events}
    by_student = {}
    for attempt in attempts:
        by_student.setdefault(str(attempt["student_id"]), []).append(attempt)
    rows = []
    config = ampa_config or {}
    for student_id, student_attempts in by_student.items():
        history = []
        ordered = sorted(student_attempts, key=lambda row: (_time(row["timestamp"]), int(row["attempt_id"])))
        for attempt in ordered:
            stamp = _time(attempt["timestamp"])
            event = event_map.get(str(attempt["attempt_id"]))
            question = question_map.get(str(attempt["question_id"]))
            if event is None or question is None:
                raise ValueError(f"missing linked row for attempt {attempt['attempt_id']}")
            error_type = str(event["error_type"])
            if error_type in MISTAKE_CLASSES:
                context = {"topic": question["topic"], "subtopic": question.get("subtopic"),
                           "difficulty": float(question["difficulty"])}
                features = class_feature_matrix(
                    history, stamp, context,
                    decay_rate=config.get("decay_rate", 0.08),
                    repetition_alpha=config.get("repetition_alpha", 0.5),
                    memory_scale=config.get("memory_scale", 3.0),
                    momentum_window=config.get("momentum_window", 5),
                    momentum_scale=config.get("momentum_scale", 0.25),
                    concept_pairs=config.get("concept_pairs") or DEFAULT_CONCEPT_PAIRS,
                )
                rows.append({
                    "student_id": student_id, "attempt_id": str(attempt["attempt_id"]),
                    "timestamp": stamp, "target": error_type, "features": features,
                    "prior_count": len(history), "prior_history": tuple(history),
                    "context": context,
                })
            # The current target is added after its features are fixed, making it
            # available only to later targets for the same student.
            history.append({
                "student_id": student_id, "attempt_id": str(attempt["attempt_id"]),
                "timestamp": stamp, "error_type": error_type,
                "correct": str(attempt["correct"]).lower() in {"true", "1"},
                "response_time": float(attempt["response_time"]),
                "topic": question["topic"], "subtopic": question.get("subtopic"),
                "difficulty": float(question["difficulty"]),
            })
    return sorted(rows, key=lambda row: (row["timestamp"], int(row["attempt_id"])))


def chronological_split(examples, train_ratio=0.70, validation_ratio=0.15, test_ratio=0.15):
    """Split target examples globally by time without shuffling student sequences."""
    ratios = (train_ratio, validation_ratio, test_ratio)
    if any(ratio <= 0 for ratio in ratios) or abs(sum(ratios) - 1.0) > 1e-9:
        raise ValueError("split ratios must be positive and sum to 1")
    ordered = sorted(examples, key=lambda row: (row["timestamp"], int(row["attempt_id"])))
    if len(ordered) < 3:
        raise ValueError("at least three next-mistake examples are needed for temporal splitting")
    train_end = max(1, min(len(ordered) - 2, int(len(ordered) * train_ratio)))
    validation_end = max(train_end + 1, min(len(ordered) - 1, int(len(ordered) * (train_ratio + validation_ratio))))
    return {"train": ordered[:train_end], "validation": ordered[train_end:validation_end], "test": ordered[validation_end:]}


def assert_temporal_order(splits):
    latest_train = max(row["timestamp"] for row in splits["train"])
    earliest_validation = min(row["timestamp"] for row in splits["validation"])
    latest_validation = max(row["timestamp"] for row in splits["validation"])
    earliest_test = min(row["timestamp"] for row in splits["test"])
    if latest_train > earliest_validation or latest_validation > earliest_test:
        raise ValueError("temporal split overlaps or is out of chronological order")


def _time(value):
    return value if isinstance(value, datetime) else datetime.fromisoformat(str(value).replace("Z", "+00:00"))
