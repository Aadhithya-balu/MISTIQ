"""UTC helpers for consistent timestamps at API boundaries."""

from datetime import datetime, timezone


def as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def utc_isoformat(value: datetime) -> str:
    return as_utc(value).isoformat().replace("+00:00", "Z")
