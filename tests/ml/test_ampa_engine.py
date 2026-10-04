from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np

from backend.ml.ampa import MISTIQAMPA
from backend.ml.ampa.features import MISTAKE_CLASSES, class_feature_matrix
from backend.ml.ampa.memory import mistake_memory, recency_weight, repetition_amplification
from backend.ml.ampa.momentum import risk_momentum
from backend.ml.ampa.optimizer import batch_gradients, numerical_gradient
from backend.ml.ampa.risk import class_risk, softmax, stability_to_instability


def test_softmax_sums_to_one_and_is_stable_for_large_logits():
    probabilities = softmax(np.array([[9000.0, 9001.0, 8999.0], [-1e6, -1e6, -1e6]]))
    assert np.all(np.isfinite(probabilities))
    assert np.allclose(probabilities.sum(axis=1), 1.0)


def test_recency_and_sublinear_repetition():
    assert recency_weight(1) > recency_weight(30)
    amplifications = [repetition_amplification(count) for count in (1, 5, 20)]
    assert amplifications[0] < amplifications[1] < amplifications[2]
    assert (amplifications[2] - amplifications[1]) < 15 * (amplifications[1] - amplifications[0])


def test_aggregated_memory_uses_exponential_recency_and_repetition():
    now = datetime(2025, 2, 1, tzinfo=timezone.utc)
    recent = [{"error_type": "CARELESS_ERROR", "timestamp": now - timedelta(days=1)}]
    old = [{"error_type": "CARELESS_ERROR", "timestamp": now - timedelta(days=30)}]
    assert mistake_memory(recent, "CARELESS_ERROR", now)[0] > mistake_memory(old, "CARELESS_ERROR", now)[0]


def test_momentum_direction_and_insufficient_history():
    up, low_info = risk_momentum([0.2, 0.3, 0.4, 0.5], window=2)
    down, _ = risk_momentum([0.6, 0.5, 0.4, 0.3], window=2)
    assert up > 0 and down < 0 and not low_info
    assert risk_momentum([0.1, 0.2], window=2) == (0.0, True)


def test_stability_is_transformed_to_protective_instability():
    assert stability_to_instability(np.array([0.9]))[0] < stability_to_instability(np.array([0.2]))[0]
    weights = np.zeros((2, 8)); weights[:, 6] = 1.0
    bias = np.zeros(2)
    stable = np.zeros((1, 2, 8)); unstable = stable.copy()
    stable[:, :, 6] = stability_to_instability(np.array(0.9))
    unstable[:, :, 6] = stability_to_instability(np.array(0.2))
    assert class_risk(stable, weights, bias)[0, 0] < class_risk(unstable, weights, bias)[0, 0]


def test_analytical_gradient_matches_finite_difference():
    rng = np.random.default_rng(4)
    x = rng.normal(size=(5, 3, 4))
    y = np.array([0, 1, 2, 1, 0])
    weights, bias = rng.normal(size=(3, 4)) * 0.1, rng.normal(size=3) * 0.1
    analytical = batch_gradients(x, y, weights, bias, 0.03)
    numerical = numerical_gradient(x, y, weights, bias, 0.03)
    assert np.allclose(analytical[0], numerical[0], atol=1e-6, rtol=1e-5)
    assert np.allclose(analytical[1], numerical[1], atol=1e-6, rtol=1e-5)


def _training_data():
    rng = np.random.default_rng(77)
    x = rng.uniform(0.05, 0.95, (60, 7, 8))
    # Controlled, learnable class signal: the matching feature is strong.
    labels = np.arange(60) % 3
    for row, label in enumerate(labels):
        x[row, label, 0] = 0.95
        x[row, (label + 1) % 7, 0] = 0.05
    names = np.asarray(MISTAKE_CLASSES)
    return x, names[labels]


def test_training_reduces_loss_and_repeats_deterministically():
    x, y = _training_data()
    first = MISTIQAMPA(seed=11, learning_rate=0.08, epochs=180, regularization=0.001).fit(x, y)
    second = MISTIQAMPA(seed=11, learning_rate=0.08, epochs=180, regularization=0.001).fit(x, y)
    assert first.loss_history_[-1] < first.loss_history_[0]
    assert not np.allclose(first.weights_, np.zeros_like(first.weights_))
    assert np.allclose(first.weights_, second.weights_)
    assert np.allclose(first.predict_proba(x[:3]), second.predict_proba(x[:3]))
    assert np.allclose(first.predict_proba(x[:3]).sum(axis=1), 1.0)
    result = first.predict(x[:1], {"attempt_count": 35, "relevant_count": 25})
    assert result["predicted_error"] in MISTAKE_CLASSES
    assert abs(sum(result["probabilities"].values()) - 1.0) < 1e-10


def test_repeated_concept_confusion_increases_student_feature():
    now = datetime(2025, 4, 1, tzinfo=timezone.utc)
    repeated = [{"student_id": 1, "topic": "Precision", "difficulty": 3,
                 "error_type": "CONCEPT_CONFUSION", "timestamp": now - timedelta(days=10-i)}
                for i in range(8)]
    comparison = [{"student_id": 2, "topic": "Precision", "difficulty": 3,
                   "error_type": "CORRECT", "timestamp": now - timedelta(days=10-i)}
                  for i in range(8)]
    a = class_feature_matrix(repeated, now, {"topic": "Precision"})
    b = class_feature_matrix(comparison, now, {"topic": "Precision"})
    concept_index = MISTAKE_CLASSES.index("CONCEPT_CONFUSION")
    assert a[concept_index, 5] > b[concept_index, 5]
    assert a[concept_index, 0] > b[concept_index, 0]


def test_concept_pair_feature_uses_matching_subtopic_with_shared_topic():
    now = datetime(2025, 4, 1, tzinfo=timezone.utc)
    history = [{"student_id": 1, "topic": "Machine Learning", "subtopic": "Precision",
                "difficulty": 3, "error_type": "CONCEPT_CONFUSION",
                "timestamp": now - timedelta(days=2)}]
    features = class_feature_matrix(
        history, now, {"topic": "Machine Learning", "subtopic": "Precision"},
    )
    index = MISTAKE_CLASSES.index("CONCEPT_CONFUSION")
    assert features[index, 5] == 1.0


def test_model_subtopic_features_match_authoritative_feature_pipeline():
    now = datetime(2025, 4, 1, tzinfo=timezone.utc)
    model = MISTIQAMPA(epochs=5).fit(*_training_data())
    event = {"student_id": "learner", "attempt_id": 1, "timestamp": now - timedelta(days=1),
             "topic": "Machine Learning", "subtopic": "Precision", "difficulty": 3,
             "correct": False, "error_type": "CONCEPT_CONFUSION", "response_time": 30}
    model.update(event)
    expected = class_feature_matrix(
        [event], now, {"topic": "Machine Learning", "subtopic": "Precision"},
    )
    actual = model.extract_student_features(
        "learner", {"topic": "Machine Learning", "subtopic": "Precision", "as_of": now},
    )
    assert np.allclose(actual, expected)


def test_repeated_confusion_history_increases_learned_class_risk():
    x, y = _training_data()
    model = MISTIQAMPA(seed=11, learning_rate=0.08, epochs=180, regularization=0.001).fit(x, y)
    now = datetime(2025, 4, 1, tzinfo=timezone.utc)
    for student_id, error in (("repeat", "CONCEPT_CONFUSION"), ("steady", "CORRECT")):
        for index in range(20):
            correct = error == "CORRECT"
            model.update({"student_id": student_id, "attempt_id": index + 1,
                          "timestamp": now - timedelta(days=20-index), "topic": "Precision",
                          "difficulty": 3, "correct": correct,
                          "error_type": error, "response_time": 30})
    a = model.predict_for_student("repeat", {"topic": "Precision", "as_of": now})
    b = model.predict_for_student("steady", {"topic": "Precision", "as_of": now})
    assert a["probabilities"]["CONCEPT_CONFUSION"] > b["probabilities"]["CONCEPT_CONFUSION"]


def test_future_events_do_not_change_past_features_or_prediction():
    model = MISTIQAMPA(epochs=20).fit(*_training_data())
    start = datetime(2025, 1, 1, tzinfo=timezone.utc)
    for i in range(6):
        model.update({"student_id": "S1", "attempt_id": i + 1,
                      "timestamp": start + timedelta(days=i), "topic": "Precision",
                      "difficulty": 3, "correct": i % 2 == 0,
                      "error_type": "CORRECT" if i % 2 == 0 else "CONCEPT_CONFUSION",
                      "response_time": 30 + i})
    as_of = start + timedelta(days=6)
    before_features = model.extract_student_features("S1", {"topic": "Precision", "as_of": as_of})
    before_prediction = model.predict_for_student("S1", {"topic": "Precision", "as_of": as_of})
    model.update({"student_id": "S1", "attempt_id": 7,
                  "timestamp": start + timedelta(days=7), "topic": "Precision",
                  "difficulty": 5, "correct": False, "error_type": "DIFFICULTY_FAILURE",
                  "response_time": 800})
    after_features = model.extract_student_features("S1", {"topic": "Precision", "as_of": as_of})
    after_prediction = model.predict_for_student("S1", {"topic": "Precision", "as_of": as_of})
    assert np.allclose(before_features, after_features)
    assert before_prediction == after_prediction


def test_cold_start_online_update_explanation_and_persistence():
    x, y = _training_data()
    model = MISTIQAMPA(seed=9, epochs=80).fit(x, y)
    cold = model.predict_for_student("new", {"topic": "Precision"})
    assert cold["confidence_level"] == "NO_RELIABLE_PREDICTION"
    assert cold["predicted_error"] is None
    start = datetime(2025, 5, 1, tzinfo=timezone.utc)
    history = []
    for i in range(7):
        item = {"student_id": "new", "attempt_id": i + 1,
                "timestamp": start + timedelta(days=i), "topic": "Precision",
                "difficulty": 2, "correct": False, "error_type": "CONCEPT_CONFUSION",
                "response_time": 42}
        history.append(item)
        model.update(item)
    result = model.predict_for_student("new", {"topic": "Precision"})
    assert result["predicted_error"] in MISTAKE_CLASSES
    assert 0 <= result["confidence"] <= result["probability"] <= 1
    explanation = model.explain_student("new", {"topic": "Precision"})
    assert explanation["prediction"] in MISTAKE_CLASSES
    assert all({"feature_value", "learned_weight", "contribution"} <= reason.keys()
               for reason in explanation["reasons"])
    path = Path(__file__).resolve().parents[2] / ".test-model.npz"
    model.save(path)
    loaded = MISTIQAMPA(seed=999).load(path)
    assert loaded.student_state.count("new") == 0
    assert np.allclose(model.predict_proba(x[:2]), loaded.predict_proba(x[:2]))
    for item in history:
        loaded.update(item)
    fixed_context = {"topic": "Precision", "as_of": (start + timedelta(days=8)).isoformat()}
    assert model.predict_for_student("new", fixed_context) == loaded.predict_for_student("new", fixed_context)


def test_fit_interactions_uses_only_prior_student_events():
    start = datetime(2025, 6, 1, tzinfo=timezone.utc)
    rows = []
    for index in range(56):
        error = MISTAKE_CLASSES[index % len(MISTAKE_CLASSES)]
        rows.append({"student_id": index % 2 + 1, "attempt_id": index + 1,
                     "question_id": index + 1, "timestamp": start + timedelta(hours=index),
                     "topic": "Precision" if index % 2 else "Recall", "difficulty": index % 5 + 1,
                     "selected_option": "A", "correct": False, "response_time": 40 + index,
                     "error_type": error})
    model = MISTIQAMPA(seed=3, epochs=15).fit_interactions(rows)
    assert model.fitted_
    assert model.training_metadata_["examples"] == len(rows)
    assert np.isfinite(model.loss_history_).all()
