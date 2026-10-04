"""Bounded directional risk momentum with a low-information cold window."""

import math
from collections.abc import Sequence


def risk_momentum(risk_history: Sequence[float], *, window: int = 5, scale: float = 0.25) -> tuple[float, bool]:
    """Compare two k-risk windows and return tanh(delta/scale), low-info flag."""
    if window < 1 or scale <= 0:
        raise ValueError("window and scale must be positive")
    if len(risk_history) < 2 * window:
        return 0.0, True
    recent = sum(risk_history[-window:]) / window
    previous = sum(risk_history[-2 * window:-window]) / window
    return math.tanh((recent - previous) / scale), False
