from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.main import create_app
from app.models import Attempt, LearnerState, MistakeEvent, Prediction, Question, Recommendation, Student
from app.services.ampa_service import AMPAService
from app.services.showcase_service import (
    DEMO_STUDENT_ID,
    reset_demo_student,
    seed_demo_history,
    setup_showcase_in_normal_db,
)

ROOT = Path(__file__).resolve().parents[2]
ARTIFACT = ROOT / "backend" / "ml" / "artifacts" / "ampa.npz"


def make_showcase_app():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    service = AMPAService(ARTIFACT)
    service.load_once()
    return engine, service


def _count(session, model):
    return session.scalar(select(func.count()).select_from(model)) or 0


def test_showcase_seed_state_and_learning_aware_recommendation():
    engine, service = make_showcase_app()
    result = setup_showcase_in_normal_db(engine, service)

    assert result["student_id"] == DEMO_STUDENT_ID
    assert result["attempt_count"] == 16
    assert result["mistake_count"] == 5
    assert result["has_prediction"] is True
    assert result["prediction_error"] == "CONCEPT_CONFUSION"
    assert result["prediction_status"] == "MEDIUM_CONFIDENCE"
    assert result["latest_mistake_error_type"] == "CONCEPT_CONFUSION"
    assert result["has_learner_state"] is True
    assert result["recommended_question_id"] == 507
    assert result["recommended_topic"] == "Precision"
    assert result["recommendation_type"] == "STARTER_PRACTICE"

    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    with factory() as session:
        assert _count(session, Question) == 14
        assert _count(session, Attempt) == 16
        assert _count(session, MistakeEvent) == 5
        assert _count(session, Prediction) == 12
        assert _count(session, Recommendation) == 1
        recommendation = session.scalar(select(Recommendation).where(
            Recommendation.student_id == DEMO_STUDENT_ID
        ))
        assert recommendation.type == "STARTER_PRACTICE"
        assert recommendation.question_id == 507
        assert recommendation.score is not None
        assert set(recommendation.score_components) == {
            "learning_need", "mistake_relevance", "difficulty_fit", "novelty", "retention_value",
        }
        assert "Precision" in recommendation.reason


def test_demo_explanation_evidence_and_completion_loop_against_real_api():
    engine, service = make_showcase_app()
    setup_showcase_in_normal_db(engine, service)
    application = create_app(database_engine=engine, ampa_service=service)
    with TestClient(application) as client:
        explanation = client.get("/api/predictions/1/latest/explanation")
        assert explanation.status_code == 200, explanation.text
        payload = explanation.json()
        assert payload["summary"]
        assert payload["reasons"]
        assert payload["top_predictions"]
        assert payload["evidence"], "demo explanation must surface contributing features"
        assert isinstance(payload["learning_need"], list)

        first = client.get("/api/recommendations/1/next").json()
        assert first["cold_start"] is True
        assert first["question"]["question_id"] == first["recommendation"]["question_id"] == 507
        assert first["recommendation"]["type"] == "STARTER_PRACTICE"

        attempted = client.post("/api/attempts", json={
            "student_id": 1, "question_id": 507, "selected_option": "A",
            "response_time": 20, "idempotency_key": "demo-507",
        })
        assert attempted.status_code == 201, attempted.text

        following = client.get("/api/recommendations/1/next").json()
        assert following["recommendation"]["id"] != first["recommendation"]["id"]
        assert following["recommendation"]["completed_at"] is None

        insight = client.get("/api/progress/1")
        assert insight.status_code == 200
        assert insight.json()["summary"]["total_attempts"] == 17
        assert insight.json()["summary"]["total_correct"] == 11 + 1


def test_demo_reset_is_isolated_to_the_demo_student():
    engine, service = make_showcase_app()
    setup_showcase_in_normal_db(engine, service)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    other_id = None
    with factory() as session:
        other = Student(name="Another learner")
        session.add(other)
        session.flush()
        other_id = other.id
        question = session.get(Question, 507)
        session.add(Attempt(
            student_id=other.id, question_id=question.question_id, selected_option="A",
            correct=True, response_time=20, attempt_number=1,
        ))
        session.commit()

    with factory() as session:
        reset_demo_student(session, service)
        session.expire_all()
        assert _count(session, Attempt) == 1
        assert _count(session, MistakeEvent) == 0
        assert _count(session, Prediction) == 0
        assert _count(session, Recommendation) == 0
        assert _count(session, LearnerState) == 0
        assert session.get(Student, DEMO_STUDENT_ID) is not None
        assert session.get(Student, other_id) is not None

    with factory() as session:
        seeded = seed_demo_history(session, service)
    assert seeded["attempts_seeded"] == 16
    with factory() as session:
        assert _count(session, Attempt) == 17
        assert _count(session, MistakeEvent) == 5