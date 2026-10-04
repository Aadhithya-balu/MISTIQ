"""Canonical tabular schemas and validation for educational interactions."""

from datetime import datetime
from typing import Mapping, Sequence

try:
    from backend.app.core.error_types import ErrorType
except ModuleNotFoundError:
    from app.core.error_types import ErrorType

QUESTION_FIELDS = (
    "question_id", "topic", "subtopic", "difficulty", "question_text",
    "option_a", "option_b", "option_c", "option_d", "correct_option",
    "estimated_time", "error_mapping",
)
ATTEMPT_FIELDS = (
    "attempt_id", "student_id", "question_id", "selected_option", "correct",
    "response_time", "timestamp", "attempt_number",
)
MISTAKE_EVENT_FIELDS = (
    "mistake_event_id", "student_id", "attempt_id", "error_type", "topic",
    "subtopic", "timestamp",
)
INTERACTION_FIELDS = (
    "student_id", "question_id", "topic", "subtopic", "difficulty",
    "selected_option", "correct_option", "correct", "response_time",
    "attempt_number", "timestamp", "error_type",
)
DIFFICULTY_LABELS = {1: "Very Easy", 2: "Easy", 3: "Medium", 4: "Hard", 5: "Very Hard"}
ERROR_TYPES = tuple(error_type.value for error_type in ErrorType)
MIN_RESPONSE_TIME = 1.0
MAX_RESPONSE_TIME = 900.0


class DatasetValidationError(ValueError):
    """Raised with a specific reason when generated or loaded data is invalid."""


def validate_dataset(
    questions: Sequence[Mapping],
    attempts: Sequence[Mapping],
    mistake_events: Sequence[Mapping],
    *,
    min_response_time: float = MIN_RESPONSE_TIME,
    max_response_time: float = MAX_RESPONSE_TIME,
) -> None:
    """Validate required fields, references, categorical values, and chronology."""
    _check_fields(questions, QUESTION_FIELDS, "question")
    _check_fields(attempts, ATTEMPT_FIELDS, "attempt")
    _check_fields(mistake_events, MISTAKE_EVENT_FIELDS, "mistake event")

    question_by_id = {}
    for row in questions:
        question_id = _required(row, "question_id", "question")
        _check_positive_id(question_id, "question_id")
        if question_id in question_by_id:
            raise DatasetValidationError(f"duplicate question_id: {question_id}")
        try:
            difficulty = int(row["difficulty"])
        except (TypeError, ValueError):
            raise DatasetValidationError(f"invalid difficulty for question {question_id}") from None
        if difficulty not in DIFFICULTY_LABELS:
            raise DatasetValidationError(f"invalid difficulty for question {question_id}: {difficulty}")
        if row["correct_option"] not in {"A", "B", "C", "D"}:
            raise DatasetValidationError(f"invalid correct_option for question {question_id}")
        try:
            mapping = __import__("json").loads(row["error_mapping"])
        except (TypeError, ValueError):
            raise DatasetValidationError(f"invalid error_mapping for question {question_id}") from None
        if (not isinstance(mapping, dict) or not mapping
                or any(option not in {"A", "B", "C", "D"} for option in mapping)
                or row["correct_option"] in mapping
                or any(error not in ERROR_TYPES or error == "CORRECT" for error in mapping.values())):
            raise DatasetValidationError(f"invalid error_mapping for question {question_id}")
        question_by_id[question_id] = row

    attempt_by_id = {}
    previous_time = {}
    for row in attempts:
        attempt_id = _required(row, "attempt_id", "attempt")
        student_id = _required(row, "student_id", f"attempt {attempt_id}")
        _check_positive_id(attempt_id, "attempt_id")
        _check_positive_id(student_id, f"student_id on attempt {attempt_id}")
        if attempt_id in attempt_by_id:
            raise DatasetValidationError(f"duplicate attempt_id: {attempt_id}")
        question_id = _required(row, "question_id", f"attempt {attempt_id}")
        if question_id not in question_by_id:
            raise DatasetValidationError(f"attempt {attempt_id} references missing question {question_id}")
        try:
            response_time = float(row["response_time"])
        except (TypeError, ValueError):
            raise DatasetValidationError(f"invalid response_time for attempt {attempt_id}") from None
        if not min_response_time <= response_time <= max_response_time:
            raise DatasetValidationError(f"impossible response_time for attempt {attempt_id}: {response_time}")
        if row["selected_option"] not in {"A", "B", "C", "D"}:
            raise DatasetValidationError(f"invalid selected_option for attempt {attempt_id}")
        try:
            stamp = _parse_timestamp(row["timestamp"])
        except (TypeError, ValueError):
            raise DatasetValidationError(f"invalid timestamp for attempt {attempt_id}") from None
        if student_id in previous_time and stamp < previous_time[student_id]:
            raise DatasetValidationError(f"attempt timestamps are out of order for student {student_id}")
        previous_time[student_id] = stamp
        try:
            attempt_number = int(row["attempt_number"])
        except (TypeError, ValueError):
            raise DatasetValidationError(f"invalid attempt_number for attempt {attempt_id}") from None
        if attempt_number < 1:
            raise DatasetValidationError(f"invalid attempt_number for attempt {attempt_id}")
        if _as_bool(row["correct"]) != (row["selected_option"] == question_by_id[question_id]["correct_option"]):
            raise DatasetValidationError(f"correct flag disagrees with selected option for attempt {attempt_id}")
        attempt_by_id[attempt_id] = row

    event_ids = set()
    for row in mistake_events:
        event_id = _required(row, "mistake_event_id", "mistake event")
        if event_id in event_ids:
            raise DatasetValidationError(f"duplicate mistake_event_id: {event_id}")
        event_ids.add(event_id)
        _check_positive_id(event_id, "mistake_event_id")
        attempt_id = _required(row, "attempt_id", f"mistake event {event_id}")
        if attempt_id not in attempt_by_id:
            raise DatasetValidationError(f"mistake event {event_id} references missing attempt {attempt_id}")
        if row["error_type"] not in ERROR_TYPES:
            raise DatasetValidationError(f"invalid error_type for mistake event {event_id}: {row['error_type']}")
        attempt = attempt_by_id[attempt_id]
        if (_as_bool(attempt["correct"]) and row["error_type"] != "CORRECT") or (
            not _as_bool(attempt["correct"]) and row["error_type"] == "CORRECT"
        ):
            raise DatasetValidationError(f"error_type does not match correctness for mistake event {event_id}")
        if row["student_id"] != attempt["student_id"]:
            raise DatasetValidationError(f"student_id mismatch for mistake event {event_id}")
        try:
            event_timestamp = _parse_timestamp(row["timestamp"])
        except (TypeError, ValueError):
            raise DatasetValidationError(f"invalid timestamp for mistake event {event_id}") from None
        if event_timestamp != _parse_timestamp(attempt["timestamp"]):
            raise DatasetValidationError(f"timestamp mismatch for mistake event {event_id}")
    if len(mistake_events) != len(attempts) or {row["attempt_id"] for row in mistake_events} != set(attempt_by_id):
        raise DatasetValidationError("expected exactly one mistake event per attempt")


def _check_fields(rows: Sequence[Mapping], fields: Sequence[str], label: str) -> None:
    for index, row in enumerate(rows):
        missing = [field for field in fields if field not in row or row[field] is None or row[field] == ""]
        if missing:
            raise DatasetValidationError(f"{label} row {index + 1} has missing fields: {', '.join(missing)}")


def _required(row: Mapping, field: str, label: str):
    value = row.get(field)
    if value is None or value == "":
        raise DatasetValidationError(f"{label} has missing {field}")
    return value


def _check_positive_id(value, field: str) -> None:
    try:
        valid = int(value) > 0
    except (TypeError, ValueError):
        valid = False
    if not valid:
        raise DatasetValidationError(f"invalid {field}: {value}")


def _parse_timestamp(value):
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


def _as_bool(value) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).lower() in {"true", "1", "yes"}
