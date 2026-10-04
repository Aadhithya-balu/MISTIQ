"""Shared probability alignment for independent sklearn baseline wrappers."""

import numpy as np

from ..ampa.features import MISTAKE_CLASSES


class SklearnBaseline:
    model_name = "Baseline"

    def __init__(self, estimator):
        self.estimator = estimator
        self.classes_ = tuple(MISTAKE_CLASSES)

    def fit(self, X, y):
        X = np.asarray(X, dtype=float)
        y = np.asarray(y, dtype=str)
        if len(X) == 0 or len(X) != len(y):
            raise ValueError("baseline fit requires non-empty features and matching labels")
        self.estimator.fit(X, y)
        self._fitted = True
        return self

    def predict_proba(self, X):
        if not getattr(self, "_fitted", False):
            raise RuntimeError(f"{self.model_name} must be fitted first")
        raw = self.estimator.predict_proba(np.asarray(X, dtype=float))
        aligned = np.zeros((len(raw), len(self.classes_)), dtype=float)
        for col, label in enumerate(self.estimator.classes_):
            if str(label) in self.classes_:
                aligned[:, self.classes_.index(str(label))] = raw[:, col]
        sums = aligned.sum(axis=1, keepdims=True)
        return np.divide(aligned, sums, out=np.full_like(aligned, 1 / len(self.classes_)), where=sums > 0)

    def predict(self, X):
        probabilities = self.predict_proba(X)
        return np.asarray(self.classes_)[np.argmax(probabilities, axis=1)]
