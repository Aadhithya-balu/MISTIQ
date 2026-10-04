"""Deterministic descriptive progress summaries over chronological raw attempts."""
from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import LearnerState
from app.services.analytics_data import comparable_windows, trend_from_delta
from app.services.recovery_service import analyze_recovery
from app.services.trajectory_service import build_trajectory


def accuracy(rows: list[dict]) -> float:
    return sum(bool(row["correct"]) for row in rows) / len(rows) if rows else 0.0


def compare_accuracy(rows: list[dict]) -> dict:
    comparable_size = min(settings.analytics_recent_window, len(rows) // 2)
    windows = comparable_windows(rows, window=settings.analytics_recent_window,
                                 minimum=settings.analytics_minimum_sample)
    if windows is None:
        return {"improvement_value": None, "improvement_direction": "INSUFFICIENT_DATA",
                "sample_sizes": {"recent": comparable_size, "previous": comparable_size},
                "window_size": comparable_size, "configured_window_size": settings.analytics_recent_window}
    recent, previous, size = windows
    delta = accuracy(recent) - accuracy(previous)
    return {"improvement_value": delta,
            "improvement_direction": trend_from_delta(delta, threshold=settings.analytics_trend_threshold),
            "sample_sizes": {"recent": len(recent), "previous": len(previous)},
            "window_size": size}


def _performance(rows: list[dict]) -> dict:
    attempts = len(rows)
    recent = rows[-settings.analytics_recent_window:]
    trend = compare_accuracy(rows)
    return {
        "attempts": attempts,
        "correct": sum(bool(row["correct"]) for row in rows),
        "incorrect": sum(not bool(row["correct"]) for row in rows),
        "accuracy": accuracy(rows) if attempts else None,
        "recent_accuracy": accuracy(recent) if recent else None,
        "recent_attempts": len(recent),
        "mistake_count": sum(row["mistake_event_id"] is not None for row in rows),
        "difficulty_average": sum(row["difficulty"] for row in rows) / attempts if attempts else None,
        "trend": trend["improvement_direction"],
        "trend_value": trend["improvement_value"],
        "trend_sample_sizes": trend["sample_sizes"],
    }


def build_progress(session: Session, student_id: int, history: list[dict]) -> dict:
    attempts = len(history)
    correct = sum(bool(row["correct"]) for row in history)
    mistakes = [row for row in history if row["mistake_event_id"] is not None]
    recent = history[-settings.analytics_recent_window:]
    improvement = compare_accuracy(history)
    current_streak = 0
    for row in reversed(history):
        if not row["correct"]:
            break
        current_streak += 1
    best_streak = 0
    streak = 0
    for row in history:
        streak = streak + 1 if row["correct"] else 0
        best_streak = max(best_streak, streak)

    topics: dict[str, list[dict]] = defaultdict(list)
    subtopics: dict[tuple[str, str], list[dict]] = defaultdict(list)
    difficulties: dict[int, list[dict]] = defaultdict(list)
    for row in history:
        topics[row["topic"]].append(row)
        if row["subtopic"]:
            subtopics[(row["topic"], row["subtopic"])].append(row)
        difficulties[row["difficulty"]].append(row)

    topic_rows = [{"topic": topic, **_performance(rows)} for topic, rows in sorted(topics.items())]
    subtopic_rows = [{"topic": topic, "subtopic": subtopic, **_performance(rows)}
                     for (topic, subtopic), rows in sorted(subtopics.items())]
    difficulty_rows = []
    for level in range(1, 6):
        rows = difficulties.get(level, [])
        difficulty_rows.append({
            "difficulty": level, "attempts": len(rows),
            "correct": sum(bool(row["correct"]) for row in rows),
            "incorrect": sum(not bool(row["correct"]) for row in rows),
            "accuracy": accuracy(rows) if rows else None,
            "mistake_rate": sum(not bool(row["correct"]) for row in rows) / len(rows) if rows else None,
            "average_response_time": sum(row["response_time"] for row in rows) / len(rows) if rows else None,
        })

    trajectory, difficulty_trajectory = build_trajectory(history)
    state = session.scalar(select(LearnerState).where(LearnerState.student_id == student_id))
    stability_value = state.knowledge_stability if state is not None else None
    if stability_value is None and history:
        try:
            from backend.ml.ampa.features import _learning_stability
        except ModuleNotFoundError:
            from ml.ampa.features import _learning_stability
        stability_value = float(_learning_stability(history))
    enough_stability_data = attempts >= settings.analytics_minimum_sample
    momentum_value = state.mistake_momentum if state is not None and attempts >= settings.analytics_momentum_minimum else None
    momentum_direction = "INSUFFICIENT_DATA"
    if momentum_value is not None:
        momentum_direction = "INCREASING" if momentum_value > .1 else "DECREASING" if momentum_value < -.1 else "STABLE"
    stability_status = "NEEDS_MORE_DATA"
    if enough_stability_data and stability_value is not None:
        if momentum_direction == "DECREASING":
            stability_status = "IMPROVING"
        elif stability_value >= .65:
            stability_status = "STABLE"
        else:
            stability_status = "VARIABLE"
    return {
        "summary": {
            "total_attempts": attempts, "total_correct": correct,
            "total_incorrect": attempts - correct,
            "overall_accuracy": correct / attempts if attempts else 0.0,
            "recent_accuracy": accuracy(recent) if recent else None,
            "recent_window_size": settings.analytics_recent_window,
            "recent_sample_size": len(recent),
            **improvement,
            "topics_practiced": len(topics), "mistake_count": len(mistakes),
            "repeated_mistake_count": sum(row["error_type"] == "REPEATED_MISTAKE" for row in mistakes),
            "successful_high_difficulty_attempts": sum(row["correct"] and row["difficulty"] >= 4 for row in history),
            "high_difficulty_attempts": sum(row["difficulty"] >= 4 for row in history),
            "current_streak": current_streak, "best_streak": best_streak,
        },
        "topic_performance": topic_rows,
        "subtopic_performance": subtopic_rows,
        "difficulty_performance": difficulty_rows,
        "trajectory": trajectory,
        "difficulty_trajectory": difficulty_trajectory,
        "recovery": analyze_recovery(history),
        "stability": {"value": stability_value, "status": stability_status,
                      "sample_size": attempts, "source": "learner_state" if state else "ampa_feature_calculation" if history else None},
        "mistake_momentum": {"value": momentum_value, "direction": momentum_direction,
                              "sample_size": attempts, "source": "learner_state" if state and momentum_value is not None else None},
    }
