from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.dependencies import get_ampa_service, get_db
from app.models import Attempt, LearnerState, MistakeEvent, Prediction, Question, Recommendation, Student
from app.services import research_service
from app.services.ampa_service import AMPAService
from app.core.time import utc_isoformat

router = APIRouter(prefix="/research", tags=["research"])


@router.get("/database/inspection", summary="Inspect the live database the showcase runs against")
def database_inspection(session: Session = Depends(get_db)):
    """Prove the showcase reads/writes the normal local database (mistiq.db)."""
    student_count = session.scalar(select(func.count()).select_from(Student)) or 0
    counts = {
        "students": student_count,
        "questions": session.scalar(select(func.count()).select_from(Question)) or 0,
        "attempts": session.scalar(select(func.count()).select_from(Attempt)) or 0,
        "mistake_events": session.scalar(select(func.count()).select_from(MistakeEvent)) or 0,
        "predictions": session.scalar(select(func.count()).select_from(Prediction)) or 0,
        "recommendations": session.scalar(select(func.count()).select_from(Recommendation)) or 0,
        "learner_states": session.scalar(select(func.count()).select_from(LearnerState)) or 0,
    }
    latest_attempt = session.scalar(
        select(Attempt).order_by(Attempt.timestamp.desc(), Attempt.attempt_id.desc())
    )
    latest_mistake = session.scalar(
        select(MistakeEvent).order_by(MistakeEvent.timestamp.desc(), MistakeEvent.mistake_event_id.desc())
    )
    latest_prediction = session.scalar(
        select(Prediction).order_by(Prediction.created_at.desc(), Prediction.id.desc())
    )
    return {
        "counts": counts,
        "latest_attempt": {
            "attempt_id": latest_attempt.attempt_id, "student_id": latest_attempt.student_id,
            "question_id": latest_attempt.question_id, "correct": latest_attempt.correct,
            "timestamp": utc_isoformat(latest_attempt.timestamp),
        } if latest_attempt else None,
        "latest_mistake": {
            "mistake_event_id": latest_mistake.mistake_event_id, "student_id": latest_mistake.student_id,
            "error_type": latest_mistake.error_type.value, "topic": latest_mistake.topic,
            "timestamp": utc_isoformat(latest_mistake.timestamp),
        } if latest_mistake else None,
        "latest_prediction": {
            "id": latest_prediction.id, "student_id": latest_prediction.student_id,
            "predicted_error": latest_prediction.predicted_error,
            "probability": latest_prediction.probability,
            "status": latest_prediction.status,
            "created_at": utc_isoformat(latest_prediction.created_at),
        } if latest_prediction else None,
    }


@router.get("/students/{student_id}/predictions")
def get_student_predictions(student_id: int, session: Session = Depends(get_db)):
    rows = session.scalars(select(Prediction).where(Prediction.student_id == student_id)
                           .order_by(Prediction.created_at.desc(), Prediction.id.desc()).limit(100)).all()
    return [{"id": row.id, "student_id": row.student_id, "prediction": row.predicted_error,
             "probability": row.probability, "model_version": row.model_version,
             "context_question_id": row.context_question_id, "timestamp": utc_isoformat(row.created_at)}
            for row in rows]


@router.get("/model")
def get_model(service: AMPAService = Depends(get_ampa_service)):
    return research_service.model_details(service.model)


@router.get("/model/features")
def get_features(service: AMPAService = Depends(get_ampa_service)):
    return research_service.model_details(service.model)["feature_definitions"]


@router.get("/model/parameters")
def get_parameters(service: AMPAService = Depends(get_ampa_service)):
    details = research_service.model_details(service.model)
    return {key: details[key] for key in ("model_name", "model_version", "classes", "features", "weights", "bias", "normalization", "hyperparameters", "training_metadata")}


@router.get("/prediction/{prediction_id}/trace")
def get_prediction_trace(prediction_id: int, session: Session = Depends(get_db), service: AMPAService = Depends(get_ampa_service)):
    try:
        trace = research_service.prediction_trace(session, prediction_id, service)
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    if trace is None:
        raise HTTPException(status_code=404, detail="Prediction not found")
    return trace


@router.get("/evaluation")
def get_evaluation():
    return research_service.evaluation_results()


@router.get("/evaluation/ablations")
def get_ablations():
    return research_service.ablation_results()


@router.get("/evaluation/calibration")
def get_calibration(model: str = Query("mistiq-ampa", max_length=100), seed: int = Query(42, ge=0)):
    return research_service.calibration_results(model, seed)


@router.get("/evaluation/confusion-matrix")
def get_confusion_matrix(model: str = Query("mistiq-ampa", max_length=100), seed: int = Query(42, ge=0)):
    return research_service.confusion_results(model, seed)


@router.get("/evaluation/seeds")
def get_seed_results():
    return research_service.seed_results()


@router.get("/evaluation/learning-curves")
def get_learning_curves():
    return research_service.learning_curve_results()


@router.get("/evaluation/cold-start")
def get_cold_start():
    return research_service.cold_start_results()
