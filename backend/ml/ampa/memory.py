"""Time-decayed mistake memory and logarithmic repetition amplification."""

from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Iterable, Mapping


def recency_weight(age_days: float, decay_rate: float = 0.08) -> float:
    """Exponential recency R=exp(-lambda * age), with non-negative age."""
    if decay_rate < 0:
        raise ValueError("decay_rate must be non-negative")
    return math.exp(-decay_rate * max(0.0, age_days))


def repetition_amplification(previous_occurrences: int, alpha: float = 0.5) -> float:
    """A(N)=1+alpha*log(1+N), giving sublinear repetition amplification."""
    if previous_occurrences < 0 or alpha < 0:
        raise ValueError("occurrences and alpha must be non-negative")
    return 1.0 + alpha * math.log1p(previous_occurrences)


def mistake_memory(
    events: Iterable[Mapping], error_type: str, as_of: datetime,
    *, decay_rate: float = 0.08, alpha: float = 0.5, memory_scale: float = 3.0,
) -> tuple[float, float, int]:
    """Return bounded aggregate memory, newest recency, and occurrence count."""
    if memory_scale <= 0:
        raise ValueError("memory_scale must be positive")
    relevant = sorted(
        (event for event in events if _value(event, "error_type") == error_type and _time(event) < as_of),
        key=_time,
    )
    count, total, latest = len(relevant), 0.0, 0.0
    for index, event in enumerate(relevant):
        age = max(0.0, (_utc(as_of) - _utc(_time(event))).total_seconds() / 86400.0)
        recency = recency_weight(age, decay_rate)
        latest = max(latest, recency)
        total += recency * repetition_amplification(index, alpha)  # E_i = 1
    return total / (total + memory_scale), latest, count


def _value(row: Mapping, key: str):
    return row.get(key) if isinstance(row, Mapping) else getattr(row, key)


def _time(row: Mapping) -> datetime:
    value = _value(row, "timestamp")
    return value if isinstance(value, datetime) else datetime.fromisoformat(str(value).replace("Z", "+00:00"))


def _utc(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)
