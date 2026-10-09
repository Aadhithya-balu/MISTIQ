# Showcase service
from __future__ import annotations

import time
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.models import Attempt, LearnerState, MistakeEvent, Prediction, Question, Recommendation, Student
from app.schemas.entities import AttemptCreate
from app.services.ampa_service import AMPAService
from app.services.recommendation_service import RecommendationService

DEMO_STUDENT_NAME = "Aadhi Demo Student"
DEMO_STUDENT_ID = 1


def _question(topic: str, text: str, options: list[str], difficulty: int,
              paired: str) -> dict[str, Any]:
    """Build one curated confidence question with its distractor error mapping."""
    return {
        "topic": topic, "subtopic": None, "difficulty": difficulty,
        "question_text": text, "options": options, "correct_option": "A",
        "estimated_time": 60,
        "error_mapping": {
            "B": "CONCEPT_CONFUSION", "C": "CARELESS_ERROR", "D": "CALCULATION_ERROR",
        },
        "_paired": paired,
    }


_CURATED_QUESTIONS: tuple[dict[str, Any], ...] = (
    _question("Precision", "Which metric divides true positives by all predicted positives?",
              ["Precision", "Recall", "Accuracy", "F1"], 2, "Recall"),
    _question("Recall", "Which metric divides true positives by all actual positives?",
              ["Recall", "Precision", "Accuracy", "F1"], 2, "Precision"),
    _question("Precision", "A search returns 10 items, 4 of which are relevant. Which metric is 4 divided by 10?",
              ["Precision", "Recall", "Accuracy", "F1"], 3, "Recall"),
    _question("Recall", "There are 8 relevant items and the system returns 6 of them. Which metric is 6 divided by 8?",
              ["Recall", "Precision", "Accuracy", "F1"], 3, "Precision"),
    _question("Precision", "Which metric answers: of the predicted positives, how many were correct?",
              ["Precision", "Recall", "Accuracy", "F1"], 3, "Recall"),
    _question("Recall", "Which metric answers: of the actual positives, how many were found?",
              ["Recall", "Precision", "Accuracy", "F1"], 3, "Precision"),
    _question("Precision", "When false positives are very costly, which metric matters most?",
              ["Precision", "Recall", "Accuracy", "F1"], 2, "Recall"),
    _question("Recall", "When missed positives are very costly, which metric matters most?",
              ["Recall", "Precision", "Accuracy", "F1"], 3, "Precision"),
    _question("Ridge", "Which penalty does ridge regression apply to the coefficients?",
              ["Ridge", "Lasso", "Elastic Net", "Ordinary Least Squares"], 2, "Lasso"),
    _question("Stack", "Which data structure follows last in, first out (LIFO)?",
              ["Stack", "Queue", "Tree", "Heap"], 2, "Queue"),
    _question("Mean", "Which central-tendency measure is most sensitive to extreme values?",
              ["Mean", "Median", "Mode", "Range"], 2, "Median"),
    _question("Overfitting", "Which condition typically shows low training error but high test error?",
              ["Overfitting", "Underfitting", "L2 Regularization", "Cross-Validation"], 3, "Underfitting"),
    _question("Classification", "Which task predicts a discrete label rather than a continuous number?",
              ["Classification", "Regression", "Clustering", "Ranking"], 2, "Regression"),
    _question("BFS", "Which graph traversal explores all neighbors of a node before going deeper?",
              ["Breadth-First Search", "Depth-First Search", "Dijkstra", "A* Search"], 3, "Depth-First Search"),
)


# Deterministic practice history for the demo student. The final seeded attempt is a
# Precision/Recall concept confusion on Q506; Q507 (Precision) is left unattempted so
# the live demo can exercise it against the stored prediction.
#
# Note: the Q502 (CALCULATION_ERROR) and Q508 (CARELESS_ERROR) attempts are on
# Recall-topic questions for a reason. The trained model's concept_confusion feature
# carries a negative weight for the CONCEPT_CONFUSION class, so a history whose
# Recall-topic errors are *all* confusion suppresses the concept-confusion prediction.
# Diluting the Recall context with one calculation and one careless error lets the real
# pipeline surface CONCEPT_CONFUSION on the final 506B attempt instead of CARELESS_ERROR.
_SEED_ATTEMPTS: tuple[tuple[int, str], ...] = (
    (501, "A"), (502, "D"), (503, "B"), (504, "A"), (505, "A"),
    (501, "B"), (502, "A"), (508, "C"),
    (509, "A"), (510, "A"), (511, "A"), (512, "A"), (513, "A"), (514, "A"),
    (506, "A"), (506, "B"),
)

_SEED_RESPONSE_TIME = 30.0


def get_or_create_demo_student(session: Session) -> Student:
    student = session.get(Student, DEMO_STUDENT_ID)
    if student is not None:
        if student.name != DEMO_STUDENT_NAME:
            student.name = DEMO_STUDENT_NAME
            session.commit()
            session.refresh(student)
        return student
    student = Student(id=DEMO_STUDENT_ID, name=DEMO_STUDENT_NAME)
    session.add(student)
    session.commit()
    session.refresh(student)
    return student


def reset_demo_student(session: Session, ampa_service: AMPAService | None = None) -> bool:
    """Remove the demo student's dependent rows while keeping the student identity."""
    for model in (Recommendation, Prediction, MistakeEvent, Attempt, LearnerState):
        session.execute(delete(model).where(model.student_id == DEMO_STUDENT_ID))
    session.commit()
    if ampa_service is not None and ampa_service.model is not None:
        ampa_service.model.clear_student(DEMO_STUDENT_ID)
    return True


def ensure_curated_questions(session: Session) -> int:
    """Upsert the curated demo question bank with stable IDs 501-514."""
    for index, definition in enumerate(_CURATED_QUESTIONS, start=501):
        question_id = index
        existing = session.get(Question, question_id)
        if existing is None:
            existing = Question(question_id=question_id)
            session.add(existing)
        existing.topic = definition["topic"]
        existing.subtopic = definition["subtopic"]
        existing.difficulty = definition["difficulty"]
        existing.question_text = definition["question_text"]
        existing.option_a, existing.option_b = definition["options"][0], definition["options"][1]
        existing.option_c, existing.option_d = definition["options"][2], definition["options"][3]
        existing.correct_option = definition["correct_option"]
        existing.estimated_time = definition["estimated_time"]
        existing.error_mapping = definition["error_mapping"]
    session.commit()
    return len(_CURATED_QUESTIONS)


def seed_demo_history(session: Session, ampa_service: AMPAService) -> dict[str, Any]:
    """Replay the curated history through the same pipeline as POST /attempts.

    Commit happens inside each submit_attempt call, and a small delay keeps
    timestamps strictly monotonic so the in-memory student state stays consistent.
    """
    seeded = 0
    for index, (question_id, selected_option) in enumerate(_SEED_ATTEMPTS, start=1):
        payload = AttemptCreate(
            student_id=DEMO_STUDENT_ID, question_id=question_id,
            selected_option=selected_option, response_time=_SEED_RESPONSE_TIME,
            idempotency_key=f"showcase-{index:03d}",
        )
        ampa_service.submit_attempt(session, payload)
        seeded += 1
        time.sleep(0.006)
    latest = session.scalar(
        select(Prediction).where(Prediction.student_id == DEMO_STUDENT_ID)
        .order_by(Prediction.created_at.desc(), Prediction.id.desc())
    )
    return {
        "attempts_seeded": seeded,
        "latest_prediction_error": latest.predicted_error if latest else None,
        "latest_prediction_status": latest.status if latest else None,
    }


def demo_status(session: Session) -> dict[str, Any]:
    student = session.get(Student, DEMO_STUDENT_ID)
    attempt_count = session.scalar(
        select(func.count()).select_from(Attempt).where(Attempt.student_id == DEMO_STUDENT_ID)
    ) or 0
    mistake_count = session.scalar(
        select(func.count()).select_from(MistakeEvent).where(MistakeEvent.student_id == DEMO_STUDENT_ID)
    ) or 0
    latest_prediction = session.scalar(
        select(Prediction).where(Prediction.student_id == DEMO_STUDENT_ID)
        .order_by(Prediction.created_at.desc(), Prediction.id.desc())
    )
    latest_attempt = session.scalar(
        select(Attempt).where(Attempt.student_id == DEMO_STUDENT_ID)
        .order_by(Attempt.timestamp.desc(), Attempt.attempt_id.desc())
    )
    has_learner_state = (
        session.scalar(
            select(func.count()).select_from(LearnerState).where(LearnerState.student_id == DEMO_STUDENT_ID)
        ) or 0
    ) > 0
    return {
        "student_id": DEMO_STUDENT_ID,
        "student_name": student.name if student else None,
        "seeded": student is not None and attempt_count > 0,
        "attempt_count": attempt_count,
        "mistake_count": mistake_count,
        "has_learner_state": has_learner_state,
        "latest_prediction_error": latest_prediction.predicted_error if latest_prediction else None,
        "latest_prediction_status": latest_prediction.status if latest_prediction else None,
        "latest_attempt_question_id": latest_attempt.question_id if latest_attempt else None,
    }


def setup_showcase_in_normal_db(engine, ampa_service: AMPAService) -> dict[str, Any]:
    """Create/reset the demo student, seed the curated bank, and report the result.

    This is the single entry point used by scripts/setup_showcase.py. All state is
    written through the real AMPA pipeline into the normal application database.
    """
    from sqlalchemy.orm import sessionmaker
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    with session_factory() as session:
        demo = get_or_create_demo_student(session)
        reset_demo_student(session, ampa_service)
        ensure_curated_questions(session)
        seeded = seed_demo_history(session, ampa_service)
        recommender = RecommendationService()
        recommendation = recommender.recommend_next(session, demo.id)
        session.commit()
        try:
            recommended_question = recommendation.question
            recommended_topic = recommended_question.subtopic or recommended_question.topic
            recommendation_type = recommendation.type
        except AttributeError:
            recommended_topic = None
            recommendation_type = None
        latest_attempt = session.scalar(
            select(Attempt).where(Attempt.student_id == DEMO_STUDENT_ID)
            .order_by(Attempt.timestamp.desc(), Attempt.attempt_id.desc())
        )
        latest_mistake = session.scalar(
            select(MistakeEvent).where(MistakeEvent.student_id == DEMO_STUDENT_ID)
            .order_by(MistakeEvent.timestamp.desc(), MistakeEvent.mistake_event_id.desc())
        )
        latest_prediction = session.scalar(
            select(Prediction).where(Prediction.student_id == DEMO_STUDENT_ID)
            .order_by(Prediction.created_at.desc(), Prediction.id.desc())
        )
        attempt_count = session.scalar(
            select(func.count()).select_from(Attempt).where(Attempt.student_id == DEMO_STUDENT_ID)
        ) or 0
        mistake_count = session.scalar(
            select(func.count()).select_from(MistakeEvent).where(MistakeEvent.student_id == DEMO_STUDENT_ID)
        ) or 0
        has_learner_state = (
            session.scalar(
                select(func.count()).select_from(LearnerState).where(LearnerState.student_id == DEMO_STUDENT_ID)
            ) or 0
        ) > 0
        return {
            "student_id": demo.id,
            "student_name": demo.name,
            "attempt_count": attempt_count,
            "mistake_count": mistake_count,
            "has_prediction": latest_prediction is not None,
            "prediction_error": latest_prediction.predicted_error if latest_prediction else None,
            "prediction_status": latest_prediction.status if latest_prediction else None,
            "prediction_probability": latest_prediction.probability if latest_prediction else None,
            "has_learner_state": has_learner_state,
            "latest_attempt_question_id": latest_attempt.question_id if latest_attempt else None,
            "latest_mistake_error_type": latest_mistake.error_type.value if latest_mistake else None,
            "recommended_question_id": recommendation.question_id if recommendation else None,
            "recommended_topic": recommended_topic,
            "recommendation_type": recommendation_type,
            "seeded_attempts": seeded["attempts_seeded"],
        }