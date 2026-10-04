"""Faithful contribution breakdown of the selected AMPA class score."""

import numpy as np

from .features import RISK_FEATURE_NAMES


def explain_contributions(features, weights, bias, labels, probabilities):
    features = np.asarray(features, dtype=float)
    weights = np.asarray(weights, dtype=float)
    scores = np.einsum("cf,cf->c", features, weights) + bias
    winner = int(np.argmax(probabilities))
    reasons = []
    for index, name in enumerate(RISK_FEATURE_NAMES):
        contribution = float(features[winner, index] * weights[winner, index])
        reasons.append({
            "feature": name,
            "feature_value": float(features[winner, index]),
            "learned_weight": float(weights[winner, index]),
            "contribution": contribution,
        })
    reasons.sort(key=lambda item: abs(item["contribution"]), reverse=True)
    return {
        "prediction": labels[winner],
        "probability": float(probabilities[winner]),
        "risk_score": float(scores[winner]),
        "reasons": reasons,
    }
