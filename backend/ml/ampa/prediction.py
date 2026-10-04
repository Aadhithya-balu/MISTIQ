"""Prediction response, confidence tiers, and history-based reliability."""

import math


def data_reliability(attempt_count: int, relevant_count: int, *, concept_coverage: float = 1.0,
                     consistency: float = 1.0, normal_threshold: int = 30) -> float:
    """Combine history volume, query relevance, concept coverage, and consistency."""
    if attempt_count <= 0 or relevant_count <= 0:
        return 0.0
    volume = min(1.0, attempt_count / max(1, normal_threshold))
    relevance = min(1.0, relevant_count / max(1, attempt_count))
    coverage = min(1.0, max(0.0, concept_coverage))
    consistency = min(1.0, max(0.0, consistency))
    # Relevance is softened to avoid zero reliability for a sparse topic query.
    return min(1.0, max(0.0, volume * math.sqrt(relevance) * (0.5 + 0.5 * coverage) * (0.5 + 0.5 * consistency)))


def confidence_level(attempt_count: int, *, no_reliable_max=4, low_max=14, medium_max=29) -> str:
    if attempt_count <= no_reliable_max:
        return "NO_RELIABLE_PREDICTION"
    if attempt_count <= low_max:
        return "LOW_CONFIDENCE"
    if attempt_count <= medium_max:
        return "MEDIUM_CONFIDENCE"
    return "NORMAL_OPERATION"


def prediction_result(labels, probabilities, attempt_count, relevant_count, *, consistency=1.0,
                      concept_coverage=1.0, thresholds=None):
    thresholds = thresholds or {}
    level = confidence_level(
        attempt_count,
        no_reliable_max=thresholds.get("no_reliable_max", 4),
        low_max=thresholds.get("low_max", 14),
        medium_max=thresholds.get("medium_max", 29),
    )
    reliability = data_reliability(
        attempt_count, relevant_count, concept_coverage=concept_coverage,
        consistency=consistency, normal_threshold=thresholds.get("normal_threshold", 30),
    )
    if probabilities is None or len(probabilities) == 0:
        return {
            "predicted_error": None, "probability": 0.0, "probabilities": {},
            "confidence": 0.0, "confidence_level": level, "data_reliability": reliability,
        }
    best = max(range(len(probabilities)), key=lambda index: probabilities[index])
    probability = float(probabilities[best])
    if attempt_count <= thresholds.get("no_reliable_max", 4):
        return {
            "predicted_error": None, "probability": 0.0,
            "probabilities": {label: float(probabilities[index]) for index, label in enumerate(labels)},
            "confidence": 0.0, "confidence_level": level,
            "data_reliability": reliability,
        }
    return {
        "predicted_error": labels[best], "probability": probability,
        "probabilities": {label: float(probabilities[index]) for index, label in enumerate(labels)},
        "confidence": probability * reliability, "confidence_level": level,
        "data_reliability": reliability,
    }
