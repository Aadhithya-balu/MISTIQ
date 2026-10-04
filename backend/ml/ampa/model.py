"""MISTIQ-AMPA: an explicitly implemented, sequential mistake classifier.

Inputs are the eight bounded Phase 2 features in ``features.FEATURE_NAMES``.
Learning stability is converted to protective-direction instability and all
normalization parameters are learned only from the training split passed to fit.
The learned W/b are global; online student histories are held by StudentStateStore.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Mapping, Sequence

import numpy as np

from .explainer import explain_contributions
from .features import (
    DEFAULT_CONCEPT_PAIRS, FEATURE_NAMES, MISTAKE_CLASSES, RISK_FEATURE_NAMES,
    class_feature_matrix,
)
from .optimizer import train_parameters
from .prediction import confidence_level, data_reliability, prediction_result
from .risk import class_risk, softmax, stability_to_instability
from .state import StudentStateStore

MODEL_VERSION = "1.0"


class MISTIQAMPA:
    """Custom softmax model augmented with temporal memory and student state."""

    def __init__(self, learning_rate=0.05, epochs=300, regularization=0.01, seed=42,
                 *, decay_rate=0.08, repetition_alpha=0.5, memory_scale=3.0,
                 momentum_window=5, momentum_scale=0.25, no_reliable_max=4,
                 low_confidence_max=14, medium_confidence_max=29, normal_threshold=30,
                 concept_pairs=None):
        if learning_rate <= 0 or epochs < 1 or regularization < 0:
            raise ValueError("learning_rate and epochs must be positive; regularization cannot be negative")
        if decay_rate < 0 or repetition_alpha < 0 or memory_scale <= 0 or momentum_window < 1 or momentum_scale <= 0:
            raise ValueError("memory and momentum parameters must be non-negative with positive scales/windows")
        if not (0 <= no_reliable_max < low_confidence_max < medium_confidence_max < normal_threshold):
            raise ValueError("cold-start thresholds must be strictly increasing")
        self.learning_rate = float(learning_rate)
        self.epochs = int(epochs)
        self.regularization = float(regularization)
        self.seed = int(seed)
        self.decay_rate = float(decay_rate)
        self.repetition_alpha = float(repetition_alpha)
        self.memory_scale = float(memory_scale)
        self.momentum_window = int(momentum_window)
        self.momentum_scale = float(momentum_scale)
        self.thresholds = {
            "no_reliable_max": int(no_reliable_max), "low_max": int(low_confidence_max),
            "medium_max": int(medium_confidence_max), "normal_threshold": int(normal_threshold),
        }
        self.concept_pairs = tuple(concept_pairs) if concept_pairs is not None else None
        self.classes_ = tuple(MISTAKE_CLASSES)
        rng = np.random.default_rng(self.seed)
        self.weights_ = rng.normal(0.0, 0.01, (len(self.classes_), len(RISK_FEATURE_NAMES)))
        self.bias_ = np.zeros(len(self.classes_), dtype=float)
        self.feature_mean_ = None
        self.feature_scale_ = None
        self.loss_history_: list[float] = []
        self.training_metadata_ = {}
        self.fitted_ = False
        self.student_state = StudentStateStore()

    def fit(self, X, y, metadata=None):
        """Fit with explicit batch gradient descent; X may be Nx8 or Nx7x8.

        X contains raw bounded engineered features. Its feature standardizer is
        fit here on training observations only and retained for inference.
        For truly sequential examples, use fit_interactions().
        """
        raw = _feature_array(X)
        labels = np.asarray([str(getattr(value, "value", value)) for value in y], dtype=object)
        if len(raw) == 0 or len(labels) != len(raw):
            raise ValueError("fit requires a non-empty X and one target per row")
        invalid = sorted(set(labels) - set(self.classes_))
        if invalid:
            raise ValueError(f"targets must be mistake classes (CORRECT is excluded): {invalid}")
        if not np.isfinite(raw).all():
            raise ValueError("features must contain only finite values")
        transformed = _to_instability(raw)
        flattened = transformed.reshape(-1, transformed.shape[-1])
        self.feature_mean_ = flattened.mean(axis=0)
        scale = flattened.std(axis=0)
        self.feature_scale_ = np.where(scale < 1e-12, 1.0, scale)
        normalized = (transformed - self.feature_mean_) / self.feature_scale_
        target_indices = np.asarray([self.classes_.index(label) for label in labels], dtype=int)
        self.weights_, self.bias_, self.loss_history_ = train_parameters(
            normalized, target_indices, self.weights_.copy(), self.bias_.copy(),
            learning_rate=self.learning_rate, epochs=self.epochs,
            regularization=self.regularization,
        )
        self.fitted_ = True
        self.training_metadata_ = {"examples": len(labels), "classes_seen": sorted(set(labels)),
                                   "epochs": self.epochs, "seed": self.seed}
        return self

    def fit_interactions(self, interactions):
        """Build leakage-safe training examples from chronological raw interactions.

        Each mistake at time t is labeled from that interaction, while features are
        built only from the same student's interactions with timestamp strictly < t.
        """
        rows, labels, training_state = [], [], StudentStateStore()
        ordered = sorted(interactions, key=lambda row: _parse_timestamp(_get(row, "timestamp")))
        for interaction in ordered:
            student_id = _get(interaction, "student_id")
            timestamp = _get(interaction, "timestamp")
            error = _error_type(interaction)
            context = {key: _get(interaction, key) for key in ("topic", "subtopic", "difficulty")
                       if _get(interaction, key) is not None}
            if error in self.classes_:
                prior = training_state.history(student_id, before=_parse_timestamp(timestamp))
                rows.append(class_feature_matrix(
                    prior, _parse_timestamp(timestamp), context,
                    decay_rate=self.decay_rate, repetition_alpha=self.repetition_alpha,
                    memory_scale=self.memory_scale, momentum_window=self.momentum_window,
                    momentum_scale=self.momentum_scale,
                    concept_pairs=self.concept_pairs or DEFAULT_CONCEPT_PAIRS,
                ))
                labels.append(error)
            training_state.update(interaction)
        if not rows:
            raise ValueError("no mistake-class training targets found in interactions")
        self.fit(np.asarray(rows), labels)
        return self

    def predict_proba(self, X, metadata=None):
        """Return softmax probabilities for shared Nx8 or class-specific Nx7x8 inputs."""
        self._require_fitted()
        raw = _feature_array(X)
        if raw.ndim == 3 and raw.shape[1] != len(self.classes_):
            raise ValueError(f"class-specific rows must include {len(self.classes_)} candidate classes")
        normalized = ( _to_instability(raw) - self.feature_mean_) / self.feature_scale_
        return softmax(class_risk(normalized, self.weights_, self.bias_))

    def predict(self, X, metadata=None):
        """Return class, probability distribution, reliability, and confidence per row.

        A student ID delegates to history-aware prediction; numeric feature inputs
        return one result dictionary or a list of dictionaries for a batch.
        """
        if isinstance(X, (str, int)):
            return self.predict_for_student(X, metadata)
        probabilities = self.predict_proba(X, metadata)
        metadata_rows = metadata if isinstance(metadata, Sequence) and not isinstance(metadata, (str, bytes, dict)) else None
        results = []
        for index, row in enumerate(probabilities):
            item = metadata_rows[index] if metadata_rows is not None else (metadata or {})
            count = int(item.get("attempt_count", 0)) if isinstance(item, Mapping) else 0
            relevant = int(item.get("relevant_count", count)) if isinstance(item, Mapping) else count
            best = int(np.argmax(row))
            reliability = data_reliability(count, relevant, concept_coverage=item.get("concept_coverage", 1.0),
                                           consistency=item.get("consistency", 1.0),
                                           normal_threshold=self.thresholds["normal_threshold"])
            results.append({
                "predicted_error": self.classes_[best], "probability": float(row[best]),
                "probabilities": {label: float(row[class_index]) for class_index, label in enumerate(self.classes_)},
                "confidence": float(row[best]) * reliability,
                "confidence_level": confidence_level(count, **{
                    "no_reliable_max": self.thresholds["no_reliable_max"],
                    "low_max": self.thresholds["low_max"], "medium_max": self.thresholds["medium_max"]}),
                "data_reliability": reliability,
            })
        return results[0] if len(results) == 1 else results

    def predict_for_student(self, student_id, context=None):
        """Return a confidence-aware prediction using only history before context.as_of."""
        context = dict(context or {})
        as_of = _parse_timestamp(context.pop("as_of", None))
        history = self.student_state.history(student_id, before=as_of)
        attempts = len(history)
        relevant = [event for event in history if context.get("topic") is None or _get(event, "topic") == context["topic"]]
        consistency = _history_consistency(relevant)
        matrix = class_feature_matrix(
            history, as_of, context, decay_rate=self.decay_rate,
            repetition_alpha=self.repetition_alpha, memory_scale=self.memory_scale,
            momentum_window=self.momentum_window, momentum_scale=self.momentum_scale,
            concept_pairs=self.concept_pairs or _default_pairs(),
        )
        if not self.fitted_:
            return prediction_result(self.classes_, None, attempts, len(relevant), consistency=consistency, thresholds=self.thresholds)
        probabilities = self.predict_proba(matrix.reshape(1, len(self.classes_), -1))[0]
        return prediction_result(self.classes_, probabilities, attempts, len(relevant), consistency=consistency,
                                 concept_coverage=float(bool(context.get("topic")) or attempts > 0),
                                 thresholds=self.thresholds)

    def explain(self, X, metadata=None):
        """Return actual feature values, learned weights, and score contributions."""
        if isinstance(X, (str, int)):
            return self.explain_student(X, metadata)
        self._require_fitted()
        raw = _feature_array(X)
        normalized = (_to_instability(raw) - self.feature_mean_) / self.feature_scale_
        if normalized.ndim == 2:
            return [self._explain_one(np.broadcast_to(row, (len(self.classes_), len(RISK_FEATURE_NAMES))))
                    for row in normalized]
        if normalized.ndim == 3:
            return [self._explain_one(row) for row in normalized]
        return self._explain_one(np.broadcast_to(normalized, (len(self.classes_), len(RISK_FEATURE_NAMES))))

    def explain_student(self, student_id, context=None):
        context = dict(context or {})
        as_of = _parse_timestamp(context.pop("as_of", None))
        history = self.student_state.history(student_id, before=as_of)
        raw = class_feature_matrix(history, as_of, context, decay_rate=self.decay_rate,
                                   repetition_alpha=self.repetition_alpha, memory_scale=self.memory_scale,
                                   momentum_window=self.momentum_window, momentum_scale=self.momentum_scale,
                                   concept_pairs=self.concept_pairs or _default_pairs())
        return self.explain(raw[None, :, :])[0]

    def update(self, interaction):
        """Record one outcome for future student-state predictions; never retrains W/b."""
        self.student_state.update(interaction)
        return self

    def extract_student_features(self, student_id, context=None):
        """Expose class feature rows for auditing; as_of excludes same/future events."""
        context = dict(context or {})
        as_of = _parse_timestamp(context.pop("as_of", None))
        history = self.student_state.history(student_id, before=as_of)
        return class_feature_matrix(history, as_of, context, decay_rate=self.decay_rate,
                                   repetition_alpha=self.repetition_alpha, memory_scale=self.memory_scale,
                                   momentum_window=self.momentum_window, momentum_scale=self.momentum_scale,
                                   concept_pairs=self.concept_pairs or _default_pairs())

    def get_parameters(self):
        return {"W": self.weights_.copy(), "b": self.bias_.copy(),
                "feature_mean": None if self.feature_mean_ is None else self.feature_mean_.copy(),
                "feature_scale": None if self.feature_scale_ is None else self.feature_scale_.copy(),
                "classes": self.classes_, "configuration": self._configuration(),
                "training_metadata": dict(self.training_metadata_), "version": MODEL_VERSION}

    def save(self, path):
        """Persist only global learned parameters and configuration, never student state."""
        payload = {"version": MODEL_VERSION, "configuration": self._configuration(),
                   "classes": self.classes_, "training_metadata": self.training_metadata_,
                   "fitted": self.fitted_}
        with Path(path).open("wb") as stream:
            np.savez_compressed(stream, W=self.weights_, b=self.bias_,
                                feature_mean=self.feature_mean_ if self.feature_mean_ is not None else np.array([]),
                                feature_scale=self.feature_scale_ if self.feature_scale_ is not None else np.array([]),
                                metadata=np.asarray(json.dumps(payload)))

    def load(self, path):
        """Load global parameters into this model while leaving its student state empty."""
        with np.load(path, allow_pickle=False) as saved:
            metadata = json.loads(str(saved["metadata"].item()))
            if metadata.get("version") != MODEL_VERSION or tuple(metadata.get("classes", ())) != self.classes_:
                raise ValueError("incompatible AMPA model version or class labels")
            self.weights_ = saved["W"].copy()
            self.bias_ = saved["b"].copy()
            mean, scale = saved["feature_mean"], saved["feature_scale"]
            self.feature_mean_ = mean.copy() if mean.size else None
            self.feature_scale_ = scale.copy() if scale.size else None
            self.training_metadata_ = metadata.get("training_metadata", {})
            self.fitted_ = bool(metadata.get("fitted"))
            config = metadata.get("configuration", {})
            for name in ("learning_rate", "epochs", "regularization", "seed", "decay_rate",
                         "repetition_alpha", "memory_scale", "momentum_window", "momentum_scale"):
                if name in config:
                    setattr(self, name, config[name])
            if "thresholds" in config:
                self.thresholds = config["thresholds"]
            saved_pairs = config.get("concept_pairs") or []
            self.concept_pairs = tuple(tuple(pair) for pair in saved_pairs) or None
        return self

    def _prepare(self, X):
        return (_to_instability(_feature_array(X)) - self.feature_mean_) / self.feature_scale_

    def _explain_one(self, class_features):
        probabilities = softmax(class_risk(class_features[None, :, :], self.weights_, self.bias_)[0])
        return explain_contributions(class_features, self.weights_, self.bias_, self.classes_, probabilities)

    def _require_fitted(self):
        if not self.fitted_:
            raise RuntimeError("MISTIQ-AMPA must be fitted before probability inference")

    def _configuration(self):
        return {"learning_rate": self.learning_rate, "epochs": self.epochs,
                "regularization": self.regularization, "seed": self.seed,
                "decay_rate": self.decay_rate, "repetition_alpha": self.repetition_alpha,
                "memory_scale": self.memory_scale, "momentum_window": self.momentum_window,
                "momentum_scale": self.momentum_scale, "thresholds": self.thresholds,
                "concept_pairs": self.concept_pairs}


def _feature_array(X):
    array = np.asarray(X, dtype=float)
    if array.ndim == 1:
        array = array.reshape(1, -1)
    if array.ndim not in (2, 3) or array.shape[-1] != len(FEATURE_NAMES):
        raise ValueError(f"features must have final dimension {len(FEATURE_NAMES)}")
    if array.shape[0] == 0 or (array.ndim == 3 and array.shape[1] == 0):
        raise ValueError("features cannot be empty")
    if not np.isfinite(array).all():
        raise ValueError("features must contain only finite values")
    return array


def _to_instability(features):
    result = np.array(features, dtype=float, copy=True)
    result[..., 6] = stability_to_instability(result[..., 6])
    return result


def _get(row, key, default=None):
    return row.get(key, default) if isinstance(row, Mapping) else getattr(row, key, default)


def _error_type(interaction):
    value = _get(interaction, "error_type")
    if value is not None:
        return str(getattr(value, "value", value))
    correct = _get(interaction, "correct")
    return "CORRECT" if correct is True or str(correct).lower() in {"true", "1"} else "CARELESS_ERROR"


def _parse_timestamp(value):
    from datetime import datetime, timezone
    if value is None:
        return datetime.now(timezone.utc)
    result = value if isinstance(value, datetime) else datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    return result.replace(tzinfo=timezone.utc) if result.tzinfo is None else result.astimezone(timezone.utc)


def _history_consistency(history):
    if not history:
        return 0.0
    return sum(_error_type(row) == "CORRECT" for row in history) / len(history)


def _default_pairs():
    return DEFAULT_CONCEPT_PAIRS
