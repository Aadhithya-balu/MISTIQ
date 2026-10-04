"""Per-student interaction histories, isolated from global learned parameters."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from typing import Mapping


class StudentStateStore:
    def __init__(self):
        self._history = defaultdict(list)
        self._attempt_ids = defaultdict(set)

    def update(self, interaction: Mapping) -> None:
        row = dict(interaction)
        if row.get("student_id") is None or not row.get("timestamp"):
            raise ValueError("interaction requires student_id and timestamp")
        student_id = row["student_id"]
        stamp = _timestamp(row["timestamp"])
        if self._history[student_id] and stamp < _timestamp(self._history[student_id][-1]["timestamp"]):
            raise ValueError(f"interaction timestamp precedes existing history for student {student_id}")
        attempt_id = row.get("attempt_id")
        if attempt_id is not None and attempt_id in self._attempt_ids[student_id]:
            raise ValueError(f"duplicate attempt_id {attempt_id} for student {student_id}")
        if attempt_id is not None:
            self._attempt_ids[student_id].add(attempt_id)
        row["_parsed_timestamp"] = stamp
        self._history[student_id].append(row)

    def history(self, student_id, *, before: datetime | None = None) -> list[dict]:
        events = self._history.get(student_id, [])
        if before is None:
            return list(events)
        cutoff = _timestamp(before)
        return [event for event in events if event["_parsed_timestamp"] < cutoff]

    def count(self, student_id, *, before: datetime | None = None) -> int:
        return len(self.history(student_id, before=before))

    def student_ids(self):
        return tuple(self._history)

    def discard_last(self, student_id, attempt_id) -> bool:
        """Undo a staged update when its enclosing database transaction fails."""
        events = self._history.get(student_id, [])
        if not events or events[-1].get("attempt_id") != attempt_id:
            return False
        events.pop()
        self._attempt_ids[student_id].discard(attempt_id)
        if not events:
            self._history.pop(student_id, None)
            self._attempt_ids.pop(student_id, None)
        return True


def _timestamp(value) -> datetime:
    parsed = value if isinstance(value, datetime) else datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed.astimezone(timezone.utc)
