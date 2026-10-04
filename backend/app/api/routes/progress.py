from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.models import LearnerState, Student
from app.schemas.entities import ErrorResponse, LearnerState as LearnerStateRead, ProgressRead
from app.services.errors import InsufficientData, StudentNotFound
from app.services.analytics_data import load_student_history
from app.services.mistake_analytics_service import build_mistake_analytics
from app.services.progress_service import build_progress

router = APIRouter()


@router.get("/progress/{student_id}", response_model=ProgressRead, summary="Get student progress analytics",
            responses={404: {"model": ErrorResponse, "description": "Student not found"}})
@router.get("/students/{student_id}/progress", response_model=ProgressRead, summary="Get student progress analytics",
            responses={404: {"model": ErrorResponse, "description": "Student not found"}})
def get_progress(student_id: int, session: Session = Depends(get_db)):
    if session.get(Student, student_id) is None:
        raise StudentNotFound(f"Student {student_id} was not found")
    history = load_student_history(session, student_id)
    analytics = build_progress(session, student_id, history)
    mistake_analytics = build_mistake_analytics(history, student_id)
    summary = analytics["summary"]
    analytics["mistake_momentum"] = {**analytics["mistake_momentum"], "trend": mistake_analytics["trend"]}
    return ProgressRead(
        student_id=student_id, attempt_count=summary["total_attempts"],
        correct_count=summary["total_correct"], accuracy=summary["overall_accuracy"],
        mistake_count=summary["mistake_count"], **analytics,
    )


@router.get("/students/{student_id}/state", response_model=LearnerStateRead, summary="Get persisted learner state",
            responses={
                404: {"model": ErrorResponse, "description": "Student not found"},
                409: {"model": ErrorResponse, "description": "Learner state is not available yet"},
            })
def get_learner_state(student_id: int, session: Session = Depends(get_db)):
    if session.get(Student, student_id) is None:
        raise StudentNotFound(f"Student {student_id} was not found")
    state = session.scalar(select(LearnerState).where(LearnerState.student_id == student_id))
    if state is None:
        raise InsufficientData("No learner state exists before the first attempt")
    return state
