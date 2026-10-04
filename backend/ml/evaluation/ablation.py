"""Feature masking for train-time AMPA ablations."""

import numpy as np

from ..ampa.features import RISK_FEATURE_NAMES

ABLATIONS = (None, "mistake_frequency", "mistake_recency", "repetition_score",
             "difficulty_sensitivity", "behavior_pressure", "concept_confusion",
             "learning_stability", "mistake_momentum")


def apply_ablation(features, removed_feature=None):
    """Remove one feature before fitting and inference, never after training."""
    array = np.array(features, dtype=float, copy=True)
    if removed_feature is None:
        return array
    # Public feature terminology says learning_stability; AMPA's risk-facing
    # column is its transformed counterpart, instability=1-stability.
    column_name = "instability" if removed_feature == "learning_stability" else removed_feature
    if column_name not in RISK_FEATURE_NAMES:
        raise ValueError(f"unknown ablation feature: {removed_feature}")
    array[..., RISK_FEATURE_NAMES.index(column_name)] = 0.0
    return array
