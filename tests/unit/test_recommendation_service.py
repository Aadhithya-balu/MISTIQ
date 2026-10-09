from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.error_types import ErrorType
from app.db.base import Base
from app.models import Attempt, MistakeEvent, Prediction, Question, Recommendation, Student
from app.services.recommendation_service import RecommendationService, complete_recommendation

DEFAULT_WEIGHTS = {
    "learning_need": 0.35, "mistake_relevance": 0.25, "difficulty_fit": 0.20,
    "novelty": 0.10, "retention_value": 0.10,
}


@pytest.fixture()
def session():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    with factory() as db:
        yield db
    engine.dispose()


def _add_student(session, name="Learner"):
    student = Student(name=name)
    session.add(student)
    session.flush()
    return student


def _add_question(session, question_id, topic, difficulty=2, subtopic=None):
    question = Question(
        question_id=question_id, topic=topic, subtopic=subtopic, difficulty=difficulty,
        question_text=f"Question {question_id}", option_a="A", option_b="B",
        option_c="C", option_d="D", correct_option="A", estimated_time=60,
        error_mapping={"B": "CONCEPT_CONFUSION"},
    )
    session.add(question)
    session.flush()
    return question


def _add_attempt(session, student, question, selected="B", correct=False,
                 response_time=20, attempt_number=1, day=1):
    attempt = Attempt(
        student_id=student.id, question_id=question.question_id, selected_option=selected,
        correct=correct, response_time=response_time,
        timestamp=datetime(2026, 1, day, tzinfo=timezone.utc).replace(tzinfo=None),
        attempt_number=attempt_number,
    )
    session.add(attempt)
    session.flush()
    return attempt


def _add_mistake(session, student, attempt, topic, error_type=ErrorType.CONCEPT_CONFUSION, day=1):
    mistake = MistakeEvent(
        student_id=student.id, attempt_id=attempt.attempt_id, error_type=error_type,
        topic=topic, timestamp=datetime(2026, 1, day, tzinfo=timezone.utc).replace(tzinfo=None),
    )
    session.add(mistake)
    session.flush()
    return mistake


def _score(components):
    return sum(components[key] * DEFAULT_WEIGHTS[key] for key in DEFAULT_WEIGHTS)


def _assert_components_and_score(recommendation):
    components = recommendation.score_components
    assert components is not None
    assert set(components) == set(DEFAULT_WEIGHTS)
    assert all(0.0 <= value <= 1.0 for value in components.values())
    assert recommendation.score == pytest.approx(_score(components), abs=1e-12)


def test_warm_start_ranks_recent_learning_need_not_lowest_id(session):
    student = _add_student(session)
    _add_question(session, 1, "Precision", difficulty=3)
    _add_question(session, 2, "Calculus", difficulty=2)
    recall = _add_question(session, 3, "Recall", difficulty=2)
    for day in (1, 2, 3):
        attempt = _add_attempt(session, student, recall, attempt_number=day, day=day)
        _add_mistake(session, student, attempt, topic="Recall", day=day)
    session.commit()

    service = RecommendationService()
    recommendation = service.recommend_next(session, student.id)

    assert recommendation.type == "STARTER_PRACTICE"
    assert recommendation.prediction_id is None
    assert recommendation.question_id == 1
    assert "Precision" in recommendation.reason
    _assert_components_and_score(recommendation)
    assert recommendation.score_components["learning_need"] == pytest.approx(0.75)


def test_empty_history_recommends_first_question_deterministically(session):
    student = _add_student(session)
    _add_question(session, 1, "Precision", difficulty=2)
    _add_question(session, 2, "Calculus", difficulty=4)
    session.commit()

    service = RecommendationService()
    first = service.recommend_next(session, student.id)
    second = service.recommend_next(session, student.id)

    assert first.type == "STARTER_PRACTICE"
    assert first.question_id == 1
    _assert_components_and_score(first)
    assert second.id == first.id
    assert first.reason == "This question is at difficulty 2, near the level supported by your practice history."


def test_reliable_prediction_produces_scored_practice_question(session):
    student = _add_student(session)
    _add_question(session, 1, "Precision", difficulty=3)
    _add_question(session, 2, "Calculus", difficulty=2)
    recall = _add_question(session, 3, "Recall", difficulty=2)
    attempt = _add_attempt(session, student, recall)
    _add_mistake(session, student, attempt, topic="Recall")
    prediction = Prediction(
        student_id=student.id, predicted_error="CONCEPT_CONFUSION", probability=0.58,
        confidence=0.58, data_reliability=1.0, status="NORMAL_OPERATION",
        model_name="MISTIQ-AMPA", model_version="1.0",
    )
    session.add(prediction)
    session.commit()

    service = RecommendationService()
    recommendation = service.recommend_next(session, student.id)

    assert recommendation.type == "PRACTICE_QUESTION"
    assert recommendation.prediction_id == prediction.id
    assert recommendation.question_id == 1
    _assert_components_and_score(recommendation)


def test_completed_recommendation_advances_to_a_fresh_row(session):
    student = _add_student(session)
    _add_question(session, 1, "Precision", difficulty=2)
    _add_question(session, 2, "Calculus", difficulty=4)
    session.commit()

    service = RecommendationService()
    first = service.recommend_next(session, student.id)
    complete_recommendation(session, first)
    session.commit()
    second = service.recommend_next(session, student.id)

    assert second.id != first.id
    assert first.completed_at is not None
    assert second.completed_at is None
    assert session.scalar(select(Recommendation).where(
        Recommendation.student_id == student.id, Recommendation.completed_at.is_(None)
    )).id == second.id