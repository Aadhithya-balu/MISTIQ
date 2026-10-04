"""Class-specific AMPA risk, stable softmax, and cross-entropy primitives."""

import numpy as np


def class_risk(features: np.ndarray, weights: np.ndarray, bias: np.ndarray) -> np.ndarray:
    """Z_e=b_e+sum_j W_ej X_ej for shared (2D) or class-specific (3D) X."""
    features = np.asarray(features, dtype=float)
    weights = np.asarray(weights, dtype=float)
    bias = np.asarray(bias, dtype=float)
    if features.ndim == 2:
        return features @ weights.T + bias
    if features.ndim == 3:
        return np.einsum("ncf,cf->nc", features, weights) + bias
    raise ValueError("features must be a 2D or 3D array")


def softmax(logits: np.ndarray) -> np.ndarray:
    """Numerically stable softmax; handles one vector or a batch of logits."""
    values = np.asarray(logits, dtype=float)
    if values.ndim not in (1, 2) or values.shape[-1] == 0:
        raise ValueError("logits must be a non-empty vector or matrix")
    if not np.isfinite(values).all():
        raise ValueError("logits must be finite")
    shifted = values - np.max(values, axis=-1, keepdims=True)
    exponentials = np.exp(shifted)
    return exponentials / np.maximum(exponentials.sum(axis=-1, keepdims=True), np.finfo(float).tiny)


def cross_entropy(probabilities: np.ndarray, targets: np.ndarray, weights: np.ndarray | None = None, regularization: float = 0.0) -> float:
    """Mean multiclass negative log likelihood plus lambda*||W||^2."""
    probabilities = np.asarray(probabilities, dtype=float)
    targets = np.asarray(targets, dtype=int)
    if probabilities.ndim != 2 or targets.shape != (len(probabilities),):
        raise ValueError("probabilities and targets have incompatible shapes")
    if len(targets) == 0:
        raise ValueError("cross entropy requires at least one example")
    eps = np.finfo(float).eps
    loss = -np.log(np.clip(probabilities[np.arange(len(targets)), targets], eps, 1.0)).mean()
    if weights is not None:
        loss += regularization * float(np.square(weights).sum())
    return float(loss)


def stability_to_instability(stability: np.ndarray) -> np.ndarray:
    """Protective stability becomes risk-facing instability: I=1-S."""
    return 1.0 - np.asarray(stability, dtype=float)
