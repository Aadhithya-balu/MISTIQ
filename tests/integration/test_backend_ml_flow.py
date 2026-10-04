from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.main import create_app
from app.models import Attempt, LearnerState, MistakeEvent, Prediction, Question
from app.services.ampa_service import AMPAService


ROOT = Path(__file__).resolve().parents[2]
ARTIFACT = ROOT / "backend" / "ml" / "artifacts" / "ampa.npz"


def make_test_app():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    with factory() as session:
        session.add(Question(
            question_id=1, topic="Machine Learning", subtopic="Classification",
            difficulty=2, question_text="Which metric measures positive predictive value?",
            option_a="Recall", option_b="Precision", option_c="Accuracy", option_d="F1",
            correct_option="A", estimated_time=60,
            error_mapping={"B": "CONCEPT_CONFUSION", "C": "CALCULATION_ERROR", "D": "PROCEDURE_ERROR"},
        ))
        session.commit()
    service = AMPAService(ARTIFACT)
    return create_app(database_engine=engine, ampa_service=service), factory, service


def test_real_ampa_attempt_to_prediction_flow_and_cold_start():
    application, factory, service = make_test_app()
    with TestClient(application) as client:
        assert client.get("/health").json() == {"status": "ok"}
        created = client.post("/api/students", json={"name": "  Ada Learner  "})
        assert created.status_code == 201
        assert created.json()["created_at"].endswith("Z")
        student_id = created.json()["id"]
        assert client.get(f"/api/students/{student_id}").json()["name"] == "Ada Learner"
        question = client.get("/api/questions/1")
        assert question.status_code == 200
        assert "correct_option" not in question.json()

        original_weights = service.model.weights_.copy()
        original_extract = service.model.extract_student_features
        feature_observations = []

        def capture_features(student, context=None):
            matrix = original_extract(student, context)
            history = service.model.student_state.history(student)
            feature_observations.append((matrix.copy(), len(history)))
            return matrix

        service.model.extract_student_features = capture_features
        responses = []
        for index in range(5):
            answer = "A" if index in (0, 2, 4) else "B"
            response = client.post("/api/attempts", json={
                "student_id": student_id, "question_id": 1,
                "selected_option": answer, "response_time": 25,
                "idempotency_key": f"attempt-{index}",
            })
            assert response.status_code == 201, response.text
            assert response.json()["attempt"]["timestamp"].endswith("Z")
            responses.append(response.json())
            matrix, available_history = feature_observations[-1]
            assert matrix.shape == (len(service.model.classes_), 8)
            assert available_history == index + 1
            if index < 4:
                assert responses[-1]["prediction"] is None

        final = responses[-1]
        assert final["attempt"]["correct"] is True
        assert final["prediction"] is not None
        assert final["prediction"]["model"] == "MISTIQ-AMPA"
        assert final["prediction"]["timestamp"].endswith("Z")
        assert responses[1]["mistake_event"]["timestamp"].endswith("Z")
        assert final["prediction"]["probability"] != final["prediction"]["confidence"]
        assert final["prediction"]["reliability"] >= 0
        assert final["prediction_status"] == "LOW_CONFIDENCE"
        assert 1 <= len(final["prediction"]["top_predictions"]) <= 3
        top_k_total = sum(item["probability"] for item in final["prediction"]["top_predictions"])
        assert 0.0 <= top_k_total <= 1.000001
        assert client.get(f"/api/predictions/{student_id}/latest").json()["id"] == final["prediction"]["id"]

        explanation = client.get(f"/api/predictions/{student_id}/latest/explanation")
        assert explanation.status_code == 200
        assert explanation.json()["reasons"]
        assert explanation.json()["summary"]
        assert explanation.json()["top_predictions"] == final["prediction"]["top_predictions"]
        assert all(
            abs(item["contribution"] - item["value"] * item["weight"]) < 1e-8
            for item in explanation.json()["reasons"]
        )
        with factory() as session:
            assert session.scalar(select(func.count(Attempt.attempt_id))) == 5
            assert session.scalar(select(func.count(MistakeEvent.mistake_event_id))) == 2
            state = session.scalar(select(LearnerState).where(LearnerState.student_id == student_id))
            assert state.attempt_count == 5
            assert state.relevant_mistake_count == 2
            persisted = session.scalar(select(Prediction).where(Prediction.student_id == student_id))
            assert persisted.explanation["reasons"]
        assert (service.model.weights_ == original_weights).all()

        # Replaying the same idempotency key returns the existing result without another update.
        replay = client.post("/api/attempts", json={
            "student_id": student_id, "question_id": 1,
            "selected_option": "A", "response_time": 25,
            "idempotency_key": "attempt-4",
        })
        assert replay.status_code == 201
        assert replay.json()["prediction_status"] == "duplicate_request"
        with factory() as session:
            assert session.scalar(select(func.count(Attempt.attempt_id))) == 5


def test_unknown_references_and_invalid_attempt_are_rejected():
    application, _, _ = make_test_app()
    with TestClient(application) as client:
        student_id = client.post("/api/students", json={"name": "Learner"}).json()["id"]
        missing_student = client.post("/api/attempts", json={
            "student_id": 999, "question_id": 1,
            "selected_option": "A", "response_time": 12,
        })
        assert missing_student.status_code == 404
        assert missing_student.json()["error"] == "student_not_found"
        missing_question = client.post("/api/attempts", json={
            "student_id": student_id, "question_id": 999,
            "selected_option": "A", "response_time": 12,
        })
        assert missing_question.status_code == 404
        invalid = client.post("/api/attempts", json={
            "student_id": student_id, "question_id": 1,
            "selected_option": "X", "response_time": 12,
        })
        assert invalid.status_code == 422
        spoofed = client.post("/api/attempts", json={
            "student_id": student_id, "question_id": 1,
            "selected_option": "A", "response_time": 12, "correct": False,
        })
        assert spoofed.status_code == 422


def test_missing_artifact_fails_clearly_without_fake_prediction():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    service = AMPAService(ARTIFACT.with_name("missing-ampa-test.npz"))
    application = create_app(database_engine=engine, ampa_service=service)
    with TestClient(application) as client:
        student = client.post("/api/students", json={"name": "No model learner"}).json()
        response = client.post("/api/attempts", json={
            "student_id": student["id"], "question_id": 1,
            "selected_option": "A", "response_time": 20,
        })
        assert response.status_code == 503
        assert response.json()["error"] == "model_unavailable"
        assert client.get(f"/api/predictions/{student['id']}/latest").status_code == 503


def test_recommendation_cold_start_and_completion_loop_uses_real_question_and_ampa():
    application, factory, _ = make_test_app()
    with TestClient(application) as client:
        student = client.post("/api/students", json={"name": "Recommendation learner"}).json()
        student_id = student["id"]
        next_step = client.get(f"/api/recommendations/{student_id}/next")
        assert next_step.status_code == 200, next_step.text
        recommendation = next_step.json()["recommendation"]
        assert next_step.json()["cold_start"] is True
        assert next_step.json()["question"]["question_id"] == recommendation["question_id"] == 1
        assert recommendation["type"] == "STARTER_PRACTICE"
        assert recommendation["score"] is None and recommendation["score_components"] is None
        assert client.get(f"/api/recommendations/{student_id}").json()[0]["id"] == recommendation["id"]
        assert client.get(f"/api/recommendations/{student_id}/next").json()["recommendation"]["id"] == recommendation["id"]

        attempted = client.post("/api/attempts", json={
            "student_id": student_id, "question_id": recommendation["question_id"],
            "selected_option": "A", "response_time": 25, "idempotency_key": "recommended-question",
        })
        assert attempted.status_code == 201, attempted.text
        stored = client.get(f"/api/recommendations/{student_id}").json()[0]
        assert stored["completed_at"] is not None

        explicit = client.post(f"/api/recommendations/{recommendation['id']}/complete")
        assert explicit.status_code == 200
        assert explicit.json()["completed_at"] == stored["completed_at"]


def test_recommendation_prefers_unattempted_question_during_cold_start():
    application, factory, _ = make_test_app()
    with factory() as session:
        session.add(Question(
            question_id=2, topic="Machine Learning", subtopic="Classification",
            difficulty=2, question_text="Another question?", option_a="A", option_b="B",
            option_c="C", option_d="D", correct_option="A", estimated_time=60,
            error_mapping={"B": "CONCEPT_CONFUSION", "C": "CALCULATION_ERROR", "D": "PROCEDURE_ERROR"},
        ))
        session.commit()
    with TestClient(application) as client:
        student_id = client.post("/api/students", json={"name": "Novel practice learner"}).json()["id"]
        first = client.get(f"/api/recommendations/{student_id}/next").json()
        client.post("/api/attempts", json={
            "student_id": student_id, "question_id": first["question"]["question_id"],
            "selected_option": "A", "response_time": 20,
        })
        following = client.get(f"/api/recommendations/{student_id}/next").json()
        assert following["cold_start"] is True
        assert following["question"]["question_id"] == 2


def test_same_topic_different_distractor_is_not_a_repeated_mistake():
    application, factory, _ = make_test_app()
    with factory() as session:
        session.add(Question(
            question_id=2, topic="Machine Learning", subtopic="Recall", difficulty=2,
            question_text="Different concept?", option_a="A", option_b="B", option_c="C", option_d="D",
            correct_option="A", estimated_time=60,
            error_mapping={"B": "CONCEPT_CONFUSION", "C": "CALCULATION_ERROR", "D": "PROCEDURE_ERROR"},
        ))
        session.commit()
    with TestClient(application) as client:
        student_id = client.post("/api/students", json={"name": "Repeat classification learner"}).json()["id"]
        first = client.post("/api/attempts", json={"student_id": student_id, "question_id": 1,
                                  "selected_option": "B", "response_time": 20})
        second = client.post("/api/attempts", json={"student_id": student_id, "question_id": 2,
                                   "selected_option": "B", "response_time": 20})
        repeated = client.post("/api/attempts", json={"student_id": student_id, "question_id": 1,
                                    "selected_option": "B", "response_time": 20})
        assert first.json()["mistake_event"]["error_type"] == "CONCEPT_CONFUSION"
        assert second.json()["mistake_event"]["error_type"] == "CONCEPT_CONFUSION"
        assert repeated.json()["mistake_event"]["error_type"] == "REPEATED_MISTAKE"


def test_normal_operation_recommendation_uses_documented_weighted_score():
    application, _, _ = make_test_app()
    with TestClient(application) as client:
        student_id = client.post("/api/students", json={"name": "Adaptive learner"}).json()["id"]
        for index in range(30):
            response = client.post("/api/attempts", json={
                "student_id": student_id, "question_id": 1,
                "selected_option": "A" if index % 2 else "B", "response_time": 20,
                "idempotency_key": f"adaptive-{index}",
            })
            assert response.status_code == 201, response.text
        recommendation = client.get(f"/api/recommendations/{student_id}/next").json()
        row = recommendation["recommendation"]
        components = row["score_components"]
        expected = (
            0.35 * components["learning_need"] + 0.25 * components["mistake_relevance"]
            + 0.20 * components["difficulty_fit"] + 0.10 * components["novelty"]
            + 0.10 * components["retention_value"]
        )
        assert recommendation["cold_start"] is False
        assert row["type"] == "PRACTICE_QUESTION"
        assert abs(row["score"] - expected) < 1e-12


def test_phase8_real_attempt_analytics_and_historical_prefix_stays_unchanged():
    application, _, _ = make_test_app()
    with TestClient(application) as client:
        student_id = client.post("/api/students", json={"name": "Analytics learner"}).json()["id"]
        sequence = ["B", "B", "C", "A", "B", "A", "A", "A"]
        for index, selected in enumerate(sequence):
            result = client.post("/api/attempts", json={
                "student_id": student_id, "question_id": 1, "selected_option": selected,
                "response_time": 24, "idempotency_key": f"analytics-{index}",
            })
            assert result.status_code == 201, result.text
        progress_before = client.get(f"/api/progress/{student_id}")
        assert progress_before.status_code == 200, progress_before.text
        before_data = progress_before.json()
        assert before_data["summary"]["total_attempts"] == 8
        assert before_data["summary"]["mistake_count"] == 4
        assert before_data["trajectory"][-1]["attempt_number"] == 8
        assert before_data["recovery"]["window_attempts"] == 3
        assert client.get(f"/api/students/{student_id}/progress").json() == before_data

        mistake_rows = client.get(f"/api/mistakes/{student_id}")
        summary = client.get(f"/api/mistakes/{student_id}/summary")
        repeated = client.get(f"/api/mistakes/{student_id}/repeated")
        confusions = client.get(f"/api/mistakes/{student_id}/confusions")
        assert all(response.status_code == 200 for response in (mistake_rows, summary, repeated, confusions))
        assert len(mistake_rows.json()) == 4
        assert confusions.json()["edges"]
        assert confusions.json()["edges"][0]["occurrences"] >= 2

        for index in range(8, 10):
            added = client.post("/api/attempts", json={
                "student_id": student_id, "question_id": 1, "selected_option": "A",
                "response_time": 24, "idempotency_key": f"analytics-{index}",
            })
            assert added.status_code == 201, added.text
        after_data = client.get(f"/api/progress/{student_id}").json()
        assert after_data["summary"]["total_attempts"] == 10
        assert after_data["trajectory"][:8] == before_data["trajectory"]


def test_phase8_empty_student_response_is_explicit_and_safe():
    application, _, _ = make_test_app()
    with TestClient(application) as client:
        student_id = client.post("/api/students", json={"name": "New learner"}).json()["id"]
        progress = client.get(f"/api/progress/{student_id}")
        assert progress.status_code == 200, progress.text
        assert progress.json()["summary"]["total_attempts"] == 0
        assert progress.json()["summary"]["overall_accuracy"] == 0.0
        assert progress.json()["summary"]["improvement_direction"] == "INSUFFICIENT_DATA"
        assert progress.json()["trajectory"] == []
        assert progress.json()["recovery"]["recovery_rate"] is None
        mistake_summary = client.get(f"/api/mistakes/{student_id}/summary")
        assert mistake_summary.status_code == 200
        assert mistake_summary.json()["distribution"] == []
        assert mistake_summary.json()["timeline_message"] == "Keep practicing to reveal your mistake patterns."
