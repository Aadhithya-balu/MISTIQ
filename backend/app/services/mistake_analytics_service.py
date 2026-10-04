"""Descriptive mistake distributions, repeated patterns, and observed concept pairs."""
from collections import Counter, defaultdict
from datetime import date, timedelta

from app.core.config import settings
from app.services.analytics_data import comparable_windows, frequency_trend_from_delta


MISTAKE_TYPES = (
    "CONCEPT_CONFUSION", "CALCULATION_ERROR", "PROCEDURE_ERROR", "CARELESS_ERROR",
    "TIME_PRESSURE", "DIFFICULTY_FAILURE", "REPEATED_MISTAKE",
)


def build_mistake_analytics(history: list[dict], student_id: int | None = None) -> dict:
    mistakes = [row for row in history if row["mistake_event_id"] is not None]
    recent_attempts = history[-settings.analytics_recent_window:]
    distribution = Counter(row["error_type"] for row in mistakes)
    rates = []
    for error_type in MISTAKE_TYPES:
        count = distribution[error_type]
        if count == 0:
            continue
        recent_count = sum(row["error_type"] == error_type for row in recent_attempts)
        windows = comparable_windows(history, window=settings.analytics_recent_window,
                                     minimum=settings.analytics_minimum_sample)
        direction = "INSUFFICIENT_DATA"
        delta = None
        if windows:
            current, previous, size = windows
            recent_rate = sum(row["error_type"] == error_type for row in current) / size
            previous_rate = sum(row["error_type"] == error_type for row in previous) / size
            delta = recent_rate - previous_rate
            direction = frequency_trend_from_delta(delta, threshold=settings.analytics_trend_threshold)
        rates.append({
            "error_type": error_type, "occurrences": count,
            "percentage_of_mistakes": count / len(mistakes) if mistakes else 0.0,
            "recent_frequency": recent_count / len(recent_attempts) if recent_attempts else None,
            "recent_occurrences": recent_count, "trend": direction, "trend_value": delta,
        })

    repeated = _repeated_patterns(mistakes, history)
    confusions = _concept_confusions(mistakes, history)
    trend = _mistake_timeline(mistakes)
    mistake_rate_windows = comparable_windows(history, window=settings.analytics_recent_window,
                                              minimum=settings.analytics_minimum_sample)
    frequency_trend = "INSUFFICIENT_DATA"
    if mistake_rate_windows:
        current, previous, size = mistake_rate_windows
        delta = (sum(row["mistake_event_id"] is not None for row in current)
                 - sum(row["mistake_event_id"] is not None for row in previous)) / size
        frequency_trend = frequency_trend_from_delta(delta, threshold=settings.analytics_trend_threshold)
    return {
        "student_id": history[0]["student_id"] if history else student_id,
        "mistake_count": len(mistakes), "attempt_count": len(history),
        "distribution": rates,
        "recent_frequency": sum(row["mistake_event_id"] is not None for row in recent_attempts) / len(recent_attempts) if recent_attempts else None,
        "trend": frequency_trend, "timeline": trend["timeline"],
        "timeline_bucket": settings.analytics_mistake_bucket,
        "timeline_sufficient": trend["sufficient"],
        "timeline_message": None if trend["sufficient"] else "Keep practicing to reveal your mistake patterns.",
        "repeated": repeated, "confusions": confusions,
        "recent_mistakes": [
            {"mistake_event_id": row["mistake_event_id"], "student_id": row["student_id"],
             "attempt_id": row["attempt_id"], "error_type": row["error_type"], "topic": row["topic"],
             "subtopic": row["subtopic"], "timestamp": row["mistake_timestamp"]}
            for row in mistakes[-20:]
        ],
    }


def _repeated_patterns(mistakes: list[dict], history: list[dict]) -> list[dict]:
    groups: dict[tuple, list[dict]] = defaultdict(list)
    pattern_types: dict[tuple, str] = {}
    for row in mistakes:
        pair = tuple(sorted((row["correct_answer"].strip().casefold(), row["selected_answer"].strip().casefold())))
        scope = (row["topic"], row["subtopic"] or "", pair)
        if row["error_type"] == "REPEATED_MISTAKE" and scope in pattern_types:
            error_type = pattern_types[scope]
        else:
            error_type = row["error_type"]
            pattern_types.setdefault(scope, error_type)
        key = (error_type, row["topic"], row["subtopic"] or "", pair)
        groups[key].append(row)
    attempt_index = {row["attempt_id"]: index for index, row in enumerate(history)}
    result = []
    for (error_type, topic, subtopic, _pair), rows in groups.items():
        if len(rows) < 2:
            continue
        positions = [attempt_index[row["attempt_id"]] for row in rows if row["attempt_id"] in attempt_index]
        recent_positions = set(range(max(0, len(history) - settings.analytics_recent_window), len(history)))
        recent_count = sum(position in recent_positions for position in positions)
        trend = "INSUFFICIENT_DATA"
        if len(positions) >= 4:
            middle = len(positions) // 2
            older_rate = (middle / max(1, positions[middle - 1] - positions[0] + 1))
            recent_rate = ((len(positions) - middle) / max(1, positions[-1] - positions[middle] + 1))
            trend = frequency_trend_from_delta(recent_rate - older_rate, threshold=settings.analytics_trend_threshold)
        last = max((row["mistake_timestamp"] for row in rows if row["mistake_timestamp"] is not None), default=None)
        result.append({"error_type": error_type, "topic": topic, "subtopic": subtopic or None,
                       "occurrences": len(rows), "last_occurrence": last,
                       "recent_occurrences": recent_count, "trend": trend})
    return sorted(result, key=lambda row: (-row["occurrences"], -row["recent_occurrences"], row["topic"], row["error_type"]))


def _concept_confusions(mistakes: list[dict], history: list[dict]) -> dict:
    confusion_rows = []
    observed_pairs = set()
    for row in mistakes:
        pair = tuple(sorted((row["correct_answer"].strip().casefold(), row["selected_answer"].strip().casefold())))
        if row["error_type"] == "CONCEPT_CONFUSION":
            observed_pairs.add(pair)
            confusion_rows.append(row)
        elif row["error_type"] == "REPEATED_MISTAKE" and pair in observed_pairs:
            # AMPA classifies a later occurrence as REPEATED_MISTAKE; retain its
            # observed distractor pair as evidence of the original confusion.
            confusion_rows.append(row)
    groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for row in confusion_rows:
        left, right = row["correct_answer"].strip(), row["selected_answer"].strip()
        if not left or not right or left.casefold() == right.casefold():
            continue
        pair = tuple(sorted((left, right), key=str.casefold))
        groups[pair].append(row)
    attempt_index = {row["attempt_id"]: index for index, row in enumerate(history)}
    edges = []
    nodes = set()
    for pair, rows in groups.items():
        nodes.update(pair)
        positions = [attempt_index[row["attempt_id"]] for row in rows if row["attempt_id"] in attempt_index]
        recent_start = max(0, len(history) - settings.analytics_recent_window)
        recent = sum(position >= recent_start for position in positions)
        trend = "INSUFFICIENT_DATA"
        if len(history) >= 2 * settings.analytics_minimum_sample:
            size = min(settings.analytics_recent_window, len(history) // 2)
            current_start, previous_start = len(history) - size, len(history) - 2 * size
            current_rate = sum(current_start <= pos < len(history) for pos in positions) / size
            previous_rate = sum(previous_start <= pos < current_start for pos in positions) / size
            trend = frequency_trend_from_delta(current_rate - previous_rate, threshold=settings.analytics_trend_threshold)
        edges.append({"concept_a": pair[0], "concept_b": pair[1], "occurrences": len(rows),
                      "recent_occurrences": recent,
                      "last_occurrence": max((row["mistake_timestamp"] for row in rows if row["mistake_timestamp"] is not None), default=None),
                      "strength": None, "trend": trend})
    edges.sort(key=lambda edge: (-edge["occurrences"], edge["concept_a"].casefold(), edge["concept_b"].casefold()))
    return {"nodes": sorted(nodes, key=str.casefold), "edges": edges}


def _mistake_timeline(mistakes: list[dict]) -> dict:
    buckets: dict[date, int] = defaultdict(int)
    for row in mistakes:
        timestamp = row["mistake_timestamp"]
        if timestamp is None:
            continue
        day = timestamp.date()
        if settings.analytics_mistake_bucket == "daily":
            key = day
        else:
            key = day - timedelta(days=day.weekday())
        buckets[key] += 1
    points = [{"period": period.isoformat(), "occurrences": buckets[period]} for period in sorted(buckets)]
    sufficient = len(mistakes) >= settings.analytics_minimum_sample and len(points) >= 2
    return {"timeline": points, "sufficient": sufficient}
