"""Descriptive outcomes in the fixed attempt window after recorded mistakes."""
from app.core.config import settings


def analyze_recovery(history: list[dict], window: int | None = None) -> dict:
    window = window or settings.analytics_recovery_window
    mistake_positions = [index for index, row in enumerate(history) if row["mistake_event_id"] is not None]
    eligible = []
    recovered_distances = []
    for position in mistake_positions:
        following = history[position + 1:position + 1 + window]
        if len(following) < window:
            continue
        eligible.append(position)
        first_correct = next((offset + 1 for offset, row in enumerate(following) if row["correct"]), None)
        if first_correct is not None:
            recovered_distances.append(first_correct)
    eligible_count = len(eligible)
    recovery_count = len(recovered_distances)
    enough = eligible_count >= settings.analytics_minimum_sample
    return {
        "window_attempts": window,
        "recovery_count": recovery_count,
        "eligible_mistakes": eligible_count,
        "recovery_rate": recovery_count / eligible_count if enough else None,
        "average_recovery_attempts": sum(recovered_distances) / recovery_count if enough and recovery_count else None,
        "sample_sufficient": enough,
    }
