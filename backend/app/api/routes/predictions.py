from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import get_ampa_service, get_db
from app.models import Prediction, Student
from app.schemas.entities import ErrorResponse, PredictionExplanation, PredictionRead
from app.services.ampa_service import AMPAService
from app.services.errors import InsufficientData, StudentNotFound
from app.core.error_labels import ERROR_LABELS, FEATURE_LABELS
from app.core.config import settings
from app.models import MistakeEvent

router = APIRouter()


def _latest(session, student_id):
    if session.get(Student, student_id) is None:
        raise StudentNotFound(f"Student {student_id} was not found")
    prediction = session.scalar(select(Prediction).where(Prediction.student_id == student_id)
                                .order_by(Prediction.created_at.desc(), Prediction.id.desc()))
    if prediction is None:
        raise InsufficientData("No reliable prediction is available yet")
    return PredictionRead(
        id=prediction.id, student_id=prediction.student_id,
        prediction=prediction.predicted_error, probability=prediction.probability,
        confidence=prediction.confidence, reliability=prediction.data_reliability,
        status=prediction.status, model=prediction.model_name,
        model_version=prediction.model_version,
        context_question_id=prediction.context_question_id,
        timestamp=prediction.created_at,
        top_predictions=(prediction.explanation or {}).get("top_predictions", []),
    ), prediction


@router.get("/predictions/{student_id}", response_model=PredictionRead,
            summary="Get the latest stored prediction", responses={
                404: {"model": ErrorResponse, "description": "Student not found"},
                409: {"model": ErrorResponse, "description": "Insufficient interaction history"},
                503: {"model": ErrorResponse, "description": "Trained AMPA model unavailable"},
            })
def get_prediction(student_id: int, session: Session = Depends(get_db),
                   _: AMPAService = Depends(get_ampa_service)):
    return _latest(session, student_id)[0]


@router.get("/predictions/{student_id}/latest", response_model=PredictionRead,
            summary="Get the latest stored prediction", responses={
                404: {"model": ErrorResponse, "description": "Student not found"},
                409: {"model": ErrorResponse, "description": "Insufficient interaction history"},
                503: {"model": ErrorResponse, "description": "Trained AMPA model unavailable"},
            })
def get_latest_prediction(student_id: int, session: Session = Depends(get_db),
                          _: AMPAService = Depends(get_ampa_service)):
    return _latest(session, student_id)[0]


@router.get("/predictions/{student_id}/latest/explanation", response_model=PredictionExplanation,
            summary="Get the latest prediction explanation", responses={
                404: {"model": ErrorResponse, "description": "Student not found"},
                409: {"model": ErrorResponse, "description": "Insufficient interaction history"},
                503: {"model": ErrorResponse, "description": "Trained AMPA model unavailable"},
            })
def get_latest_explanation(student_id: int, session: Session = Depends(get_db),
                           _: AMPAService = Depends(get_ampa_service)):
    _, prediction = _latest(session, student_id)
    payload = dict(prediction.explanation or {})
    reasons = payload.get("reasons", [])
    significant = [reason for reason in reasons if abs(reason.get("contribution", 0)) >= settings.explanation_contribution_threshold]
    label = ERROR_LABELS.get(prediction.predicted_error, prediction.predicted_error.replace("_", " ").lower())
    payload["summary"] = f"MISTIQ estimates {label.lower()} may be a useful area to watch, based on your practice history."
    payload["evidence"] = [
        f"{FEATURE_LABELS.get(reason.get('feature'), reason.get('feature', 'practice signal').replace('_', ' '))} contributed {reason['contribution']:+.2f} to this model score."
        for reason in significant[:3]
    ]
    payload["learning_need"] = []
    if prediction.context_question_id is not None:
        from app.models import Question
        context_question = session.get(Question, prediction.context_question_id)
        if context_question:
            count = session.scalar(select(MistakeEvent.mistake_event_id).where(
                MistakeEvent.student_id == student_id, MistakeEvent.topic == context_question.topic
            ).order_by(MistakeEvent.timestamp.desc()).limit(1))
            if count:
                payload["learning_need"] = [context_question.subtopic or context_question.topic]
    payload["top_predictions"] = payload.get("top_predictions", [])
    return payload
