"""Numerically safe classification, calibration, and confusion metrics."""

import numpy as np


def evaluate_predictions(y_true, probabilities, labels, *, calibration_bins=10):
    y_true = np.asarray(y_true, dtype=str)
    probabilities = np.asarray(probabilities, dtype=float)
    labels = tuple(labels)
    if len(y_true) == 0:
        raise ValueError("cannot evaluate an empty target set")
    if probabilities.shape != (len(y_true), len(labels)):
        raise ValueError("probability matrix shape must match targets and labels")
    if len(set(labels)) != len(labels) or not set(y_true).issubset(labels):
        raise ValueError("labels must be unique and include every target class")
    if not np.isfinite(probabilities).all() or (probabilities < 0).any():
        raise ValueError("probabilities must be finite and non-negative")
    row_sums = probabilities.sum(axis=1)
    if not np.allclose(row_sums, 1.0, atol=1e-6):
        raise ValueError("each probability row must sum to 1")

    indices = np.asarray([labels.index(label) for label in y_true])
    predicted = np.argmax(probabilities, axis=1)
    confusion = np.zeros((len(labels), len(labels)), dtype=int)
    np.add.at(confusion, (indices, predicted), 1)
    per_class = {}
    precisions, recalls, f1s, supports = [], [], [], []
    for index, label in enumerate(labels):
        tp = int(confusion[index, index])
        fp = int(confusion[:, index].sum() - tp)
        fn = int(confusion[index, :].sum() - tp)
        support = int(confusion[index, :].sum())
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        per_class[label] = {"precision": precision, "recall": recall, "f1": f1, "support": support}
        precisions.append(precision); recalls.append(recall); f1s.append(f1); supports.append(support)
    supports = np.asarray(supports, dtype=float)
    true_probabilities = np.clip(probabilities[np.arange(len(y_true)), indices], np.finfo(float).tiny, 1.0)
    one_hot = np.eye(len(labels))[indices]
    top_order = np.argsort(probabilities, axis=1)[:, ::-1]
    ece, calibration = expected_calibration_error(y_true, probabilities, labels, bins=calibration_bins)
    return {
        "accuracy": float(np.mean(predicted == indices)),
        "macro_precision": float(np.mean(precisions)),
        "macro_recall": float(np.mean(recalls)),
        "macro_f1": float(np.mean(f1s)),
        "weighted_f1": float(np.average(f1s, weights=supports)) if supports.sum() else 0.0,
        "log_loss": float(-np.log(true_probabilities).mean()),
        "top2_accuracy": float(np.mean([indices[i] in top_order[i, :min(2, len(labels))] for i in range(len(y_true))])),
        "top3_accuracy": float(np.mean([indices[i] in top_order[i, :min(3, len(labels))] for i in range(len(y_true))])),
        "brier_score": float(np.mean(np.sum((probabilities - one_hot) ** 2, axis=1))),
        "ece": ece,
        "per_class": per_class,
        "confusion_matrix": confusion,
        "calibration": calibration,
    }


def expected_calibration_error(y_true, probabilities, labels, *, bins=10):
    if bins < 1:
        raise ValueError("calibration bins must be at least one")
    y_true = np.asarray(y_true, dtype=str)
    probabilities = np.asarray(probabilities, dtype=float)
    predicted = np.argmax(probabilities, axis=1)
    confidence = probabilities[np.arange(len(probabilities)), predicted]
    correct = np.asarray([labels[index] == y_true[row] for row, index in enumerate(predicted)], dtype=float)
    edges = np.linspace(0.0, 1.0, bins + 1)
    report, ece = [], 0.0
    for index in range(bins):
        in_bin = (confidence >= edges[index]) & (confidence <= edges[index + 1] if index == bins - 1 else confidence < edges[index + 1])
        count = int(in_bin.sum())
        mean_confidence = float(confidence[in_bin].mean()) if count else 0.0
        accuracy = float(correct[in_bin].mean()) if count else 0.0
        weight = count / max(1, len(y_true))
        ece += weight * abs(accuracy - mean_confidence)
        report.append({"bin": index, "lower": float(edges[index]), "upper": float(edges[index + 1]),
                       "count": count, "mean_confidence": mean_confidence, "accuracy": accuracy})
    return float(ece), report


def confusion_rows(matrix, labels):
    return [{"true_label": labels[row], "predicted_label": labels[col], "count": int(matrix[row, col])}
            for row in range(len(labels)) for col in range(len(labels))]
