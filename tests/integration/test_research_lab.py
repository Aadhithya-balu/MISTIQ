from pathlib import Path

import numpy as np
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.main import create_app
from app.models import Prediction, Question
from app.services.ampa_service import AMPAService
from backend.ml.ampa.risk import softmax

ROOT = Path(__file__).resolve().parents[2]
ARTIFACT = ROOT / "backend" / "ml" / "artifacts" / "ampa.npz"


def setup_app():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    with factory() as session:
        session.add(Question(question_id=1, topic="Machine Learning", subtopic="Metrics", difficulty=2,
                             question_text="Question?", option_a="A", option_b="B", option_c="C", option_d="D",
                             correct_option="A", estimated_time=30,
                             error_mapping={"B": "CONCEPT_CONFUSION", "C": "CALCULATION_ERROR", "D": "PROCEDURE_ERROR"}))
        session.commit()
    service = AMPAService(ARTIFACT)
    return create_app(database_engine=engine, ampa_service=service), service


def test_research_model_endpoint_returns_saved_parameters():
    app, service = setup_app()
    with TestClient(app) as client:
        payload = client.get("/api/research/model").json()
        assert payload["training_status"] == "trained"
        assert payload["weights"] == service.model.weights_.tolist()
        assert payload["bias"] == service.model.bias_.tolist()
        assert payload["normalization"]["mean"] == service.model.feature_mean_.tolist()
        assert payload["feature_count"] == 8 and payload["class_count"] == 7
        assert client.get("/api/research/model/parameters").json()["weights"] == payload["weights"]


def test_formula_trace_replays_real_prediction_deterministically():
    app, service = setup_app()
    with TestClient(app) as client:
        student = client.post("/api/students", json={"name": "Research learner"}).json()["id"]
        for index in range(5):
            response = client.post("/api/attempts", json={
                "student_id": student, "question_id": 1, "selected_option": "B" if index % 2 else "A",
                "response_time": 24, "idempotency_key": f"research-{index}",
            })
            assert response.status_code == 201, response.text
        prediction_id = response.json()["prediction"]["id"]
        first = client.get(f"/api/research/prediction/{prediction_id}/trace")
        second = client.get(f"/api/research/prediction/{prediction_id}/trace")
        assert first.status_code == 200, first.text
        trace = first.json()
        assert trace == second.json()
        assert trace["attempt_count"] == 5
        assert trace["replay_matches_stored"] is True
        assert trace["verification_status"] == "EXACT"
        assert np.isclose(sum(trace["probabilities"].values()), 1.0)
        expected = softmax(np.asarray([trace["raw_scores"][label] for label in trace["classes"]]))
        assert np.allclose(expected, [trace["probabilities"][label] for label in trace["classes"]])
        assert all(np.isclose(row["contribution"], row["value"] * row["weight"]) for row in trace["contributions"])
        winner = trace["prediction"]["predicted_error"]
        assert np.isclose(trace["raw_scores"][winner], trace["bias"][trace["classes"].index(winner)] + sum(row["contribution"] for row in trace["contributions"]))
        student_prediction = client.get(f"/api/predictions/{student}/latest").json()
        assert not ({"weights", "bias", "raw_scores", "probabilities"} & set(student_prediction))

        with app.state.SessionLocal() as session:
            stored = session.get(Prediction, prediction_id)
            explanation = dict(stored.explanation)
            snapshot = dict(explanation["research_trace_snapshot"])
            scoring = {key: dict(value) for key, value in snapshot["scoring_features_by_class"].items()}
            scoring["CONCEPT_CONFUSION"]["mistake_frequency"] += 0.1
            snapshot["scoring_features_by_class"] = scoring
            explanation["research_trace_snapshot"] = snapshot
            stored.explanation = explanation
            session.commit()
        tampered = client.get(f"/api/research/prediction/{prediction_id}/trace").json()
        assert tampered["verification_status"] == "MISMATCH"
        assert tampered["replay_matches_stored"] is False

        with app.state.SessionLocal() as session:
            stored = session.get(Prediction, prediction_id)
            explanation = dict(stored.explanation)
            snapshot = dict(explanation["research_trace_snapshot"])
            for key in ("configuration", "inference_as_of", "feature_mean", "feature_scale"):
                snapshot.pop(key)
            explanation["research_trace_snapshot"] = snapshot
            stored.explanation = explanation
            session.commit()
        legacy = client.get(f"/api/research/prediction/{prediction_id}/trace")
        assert legacy.status_code == 200, legacy.text
        assert legacy.json()["verification_status"] == "APPROXIMATE"
        assert legacy.json()["replay_matches_stored"] is None

        listing = client.get(f"/api/research/students/{student}/predictions").json()
        assert listing[0]["timestamp"].endswith("Z")


def test_phase_four_endpoints_report_real_files_and_absent_curve_honestly():
    app, _ = setup_app()
    with TestClient(app) as client:
        comparison = client.get("/api/research/evaluation").json()
        ablations = client.get("/api/research/evaluation/ablations").json()
        calibration = client.get("/api/research/evaluation/calibration").json()
        confusion = client.get("/api/research/evaluation/confusion-matrix").json()
        curves = client.get("/api/research/evaluation/learning-curves").json()
        assert comparison["available"] and comparison["results"]
        assert ablations["available"] and ablations["results"]
        assert calibration["available"] and calibration["result"]["brier_score"] > 0
        assert confusion["available"] and len(confusion["result"]["matrix"]) == len(confusion["result"]["labels"])
        assert curves["available"] is True
        assert curves["results"]
        assert {row["history_attempts"] for row in curves["results"]} >= {5, 10, 15}


def test_unknown_research_prediction_returns_404():
    app, _ = setup_app()
    with TestClient(app) as client:
        assert client.get("/api/research/prediction/999/trace").status_code == 404
