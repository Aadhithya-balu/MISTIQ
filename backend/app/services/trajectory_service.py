"""Chronological graph-ready series using prefix-only values at each point."""
from datetime import timezone

from app.core.config import settings

try:
    from backend.ml.ampa.features import learning_stability_from_counts
except ModuleNotFoundError:
    from ml.ampa.features import learning_stability_from_counts


def build_trajectory(history: list[dict]) -> tuple[list[dict], list[dict]]:
    points = []
    difficulty_points = []
    correct_count = 0
    stability_correct_count = 0
    mistake_count = 0
    for index, row in enumerate(history):
        if row["correct"]:
            correct_count += 1
        if row["error_type"] == "CORRECT":
            stability_correct_count += 1
        else:
            mistake_count += 1
        prefix = history[:index + 1]
        sample = prefix[-settings.analytics_recent_window:]
        enough_rolling = len(sample) >= settings.analytics_minimum_sample
        rolling_correct = sum(bool(item["correct"]) for item in sample)
        timestamp = row["timestamp"]
        timestamp_text = timestamp.isoformat() if timestamp else None
        if timestamp and timestamp.tzinfo is not None:
            timestamp_text = timestamp.astimezone(timezone.utc).isoformat()
        stability = learning_stability_from_counts(stability_correct_count, index + 1)
        points.append({
            "attempt_number": index + 1, "timestamp": timestamp_text,
            "accuracy": correct_count / (index + 1), "difficulty": row["difficulty"],
            "mistake_rate": mistake_count / (index + 1),
            "rolling_accuracy": rolling_correct / len(sample) if enough_rolling else None,
            "rolling_mistake_rate": (len(sample) - rolling_correct) / len(sample) if enough_rolling else None,
            "learning_stability": stability,
        })
        difficulty_points.append({
            "attempt_number": index + 1, "timestamp": timestamp_text,
            "difficulty": row["difficulty"], "correct": bool(row["correct"]),
        })
    return points, difficulty_points
