"""One chronological, database-backed source for progress and mistake analytics."""
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Attempt, MistakeEvent, Question


def load_student_history(session: Session, student_id: int) -> list[dict]:
    rows = session.execute(
        select(Attempt, Question, MistakeEvent)
        .join(Question, Attempt.question_id == Question.question_id)
        .outerjoin(MistakeEvent, MistakeEvent.attempt_id == Attempt.attempt_id)
        .where(Attempt.student_id == student_id)
    ).all()
    history = []
    for attempt, question, mistake in rows:
        selected_answer = getattr(question, f"option_{attempt.selected_option.lower()}")
        correct_answer = getattr(question, f"option_{question.correct_option.lower()}")
        history.append({
            "attempt_id": attempt.attempt_id, "student_id": attempt.student_id,
            "question_id": attempt.question_id, "attempt_number": attempt.attempt_number,
            "selected_option": attempt.selected_option, "correct": bool(attempt.correct),
            "response_time": attempt.response_time, "timestamp": attempt.timestamp,
            "topic": question.topic, "subtopic": question.subtopic,
            "difficulty": question.difficulty, "selected_answer": selected_answer,
            "correct_answer": correct_answer,
            "error_type": (mistake.error_type.value if mistake else
                           "CORRECT" if attempt.correct else "UNCLASSIFIED_ERROR"),
            "mistake_event_id": mistake.mistake_event_id if mistake else None,
            "timestamp": attempt.timestamp,
            "mistake_timestamp": mistake.timestamp if mistake else None,
        })
    return sorted(history, key=_order_key)


def _order_key(row):
    timestamp = row["timestamp"]
    if timestamp is None:
        return (datetime.min, row["attempt_id"])
    if timestamp.tzinfo is not None:
        timestamp = timestamp.astimezone(timezone.utc).replace(tzinfo=None)
    return (timestamp, row["attempt_id"])


def comparable_windows(rows: list, *, window: int, minimum: int):
    """Return equally sized adjacent windows or None when samples are too small."""
    size = min(window, len(rows) // 2)
    if size < minimum:
        return None
    return rows[-size:], rows[-2 * size:-size], size


def trend_from_delta(delta: float | None, *, threshold: float | None = None) -> str:
    if delta is None:
        return "INSUFFICIENT_DATA"
    threshold = threshold if threshold is not None else 0.0
    if delta > threshold:
        return "IMPROVING"
    if delta < -threshold:
        return "DECLINING"
    return "STABLE"


def frequency_trend_from_delta(delta: float | None, *, threshold: float | None = None) -> str:
    if delta is None:
        return "INSUFFICIENT_DATA"
    threshold = threshold if threshold is not None else 0.0
    if delta > threshold:
        return "INCREASING"
    if delta < -threshold:
        return "DECREASING"
    return "STABLE"
