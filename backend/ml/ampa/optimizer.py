"""Explicit batch-gradient training and finite-difference gradient checking."""

import numpy as np

from .risk import cross_entropy, softmax


def batch_gradients(features: np.ndarray, targets: np.ndarray, weights: np.ndarray, bias: np.ndarray,
                    regularization: float = 0.0):
    """Analytical softmax/cross-entropy gradients for 2D or class-specific 3D X."""
    x = np.asarray(features, dtype=float)
    y = np.asarray(targets, dtype=int)
    n, class_count = len(x), len(bias)
    if n == 0:
        raise ValueError("training batch cannot be empty")
    if x.ndim == 2:
        logits = x @ weights.T + bias
        grad_w = None
    elif x.ndim == 3:
        logits = np.einsum("ncf,cf->nc", x, weights) + bias
    else:
        raise ValueError("features must be a 2D or 3D array")
    p = softmax(logits)
    delta = p.copy()
    delta[np.arange(n), y] -= 1.0
    if x.ndim == 2:
        grad_w = delta.T @ x / n
    else:
        grad_w = np.einsum("nc,ncf->cf", delta, x) / n
    grad_w += 2.0 * regularization * weights
    grad_b = delta.mean(axis=0)
    return grad_w, grad_b


def numerical_gradient(features, targets, weights, bias, regularization=0.0, epsilon=1e-5):
    """Central finite differences for all W and b parameters."""
    gw, gb = np.zeros_like(weights), np.zeros_like(bias)
    for index in np.ndindex(weights.shape):
        plus, minus = weights.copy(), weights.copy()
        plus[index] += epsilon
        minus[index] -= epsilon
        gw[index] = (_loss(features, targets, plus, bias, regularization) -
                     _loss(features, targets, minus, bias, regularization)) / (2 * epsilon)
    for index in range(len(bias)):
        plus, minus = bias.copy(), bias.copy()
        plus[index] += epsilon
        minus[index] -= epsilon
        gb[index] = (_loss(features, targets, weights, plus, regularization) -
                     _loss(features, targets, weights, minus, regularization)) / (2 * epsilon)
    return gw, gb


def _loss(features, targets, weights, bias, regularization):
    x = np.asarray(features, dtype=float)
    logits = x @ weights.T + bias if x.ndim == 2 else np.einsum("ncf,cf->nc", x, weights) + bias
    return cross_entropy(softmax(logits), targets, weights, regularization)


def train_parameters(features, targets, weights, bias, *, learning_rate, epochs, regularization):
    """Full-batch gradient descent; bias is deliberately not regularized."""
    losses = []
    for _ in range(epochs):
        grad_w, grad_b = batch_gradients(features, targets, weights, bias, regularization)
        weights -= learning_rate * grad_w
        bias -= learning_rate * grad_b
        loss = _loss(features, targets, weights, bias, regularization)
        if not np.isfinite(loss) or not np.isfinite(weights).all() or not np.isfinite(bias).all():
            raise FloatingPointError("AMPA training diverged to a non-finite value")
        losses.append(loss)
    return weights, bias, losses
