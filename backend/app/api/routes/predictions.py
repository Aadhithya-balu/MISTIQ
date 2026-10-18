from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import authorize_student, get_ampa_service, get_db
from app.models import Prediction, Student, User
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
                   _: AMPAService = Depends(get_ampa_service),
                   __: User = Depends(authorize_student)):
    return _latest(session, student_id)[0]


@router.get("/predictions/{student_id}/latest", response_model=PredictionRead,
            summary="Get the latest stored prediction", responses={
                404: {"model": ErrorResponse, "description": "Student not found"},
                409: {"model": ErrorResponse, "description": "Insufficient interaction history"},
                503: {"model": ErrorResponse, "description": "Trained AMPA model unavailable"},
            })
def get_latest_prediction(student_id: int, session: Session = Depends(get_db),
                          _: AMPAService = Depends(get_ampa_service),
                          __: User = Depends(authorize_student)):
    return _latest(session, student_id)[0]


@router.get("/predictions/{student_id}/latest/explanation", response_model=PredictionExplanation,
            summary="Get the latest prediction explanation", responses={
                404: {"model": ErrorResponse, "description": "Student not found"},
                409: {"model": ErrorResponse, "description": "Insufficient interaction history"},
                503: {"model": ErrorResponse, "description": "Trained AMPA model unavailable"},
            })
def get_latest_explanation(student_id: int, session: Session = Depends(get_db),
                           _: AMPAService = Depends(get_ampa_service),
                           __: User = Depends(authorize_student)):
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


import time
import numpy as np
from pydantic import BaseModel
from fastapi import HTTPException
from app.models import LearnerState


class SimulationRequest(BaseModel):
    preset: str | None = None
    features: dict[str, float] | None = None
    attempt_count: int = 15


@router.get("/predictions/{student_id}/telemetry", summary="Get live ML telemetry, 8D feature vector, and softmax distribution")
def get_student_telemetry(student_id: int, session: Session = Depends(get_db),
                          ampa_service: AMPAService = Depends(get_ampa_service),
                          _: User = Depends(authorize_student)):
    t0 = time.perf_counter()
    if session.get(Student, student_id) is None:
        raise StudentNotFound(f"Student {student_id} was not found")

    model = ampa_service.model
    if model is None or not model.fitted_:
        raise HTTPException(status_code=503, detail="Trained AMPA model is unavailable")

    state = session.scalar(select(LearnerState).where(LearnerState.student_id == student_id))
    prediction = session.scalar(select(Prediction).where(Prediction.student_id == student_id)
                                .order_by(Prediction.created_at.desc(), Prediction.id.desc()))

    keys = [
        "mistake_frequency", "mistake_recency", "repetition_score",
        "difficulty_sensitivity", "behavior_pressure", "concept_confusion",
        "learning_stability", "mistake_momentum"
    ]

    if state is not None:
        raw_vals = [
            float(state.mistake_frequency), float(state.mistake_recency),
            float(state.repetition_score), float(state.difficulty_sensitivity),
            float(state.behavior_pressure), float(state.concept_confusion),
            float(state.knowledge_stability), float(state.mistake_momentum),
        ]
        attempt_count = state.attempt_count
    else:
        raw_vals = [0.1, 0.1, 0.0, 0.2, 0.1, 0.1, 0.8, 0.0]
        attempt_count = 0

    instability = 1.0 - raw_vals[6]
    risk_vector = np.array([
        raw_vals[0], raw_vals[1], raw_vals[2],
        raw_vals[3], raw_vals[4], raw_vals[5],
        instability, raw_vals[7]
    ], dtype=float)

    mean = model.feature_mean_ if model.feature_mean_ is not None else np.zeros(8)
    scale = model.feature_scale_ if model.feature_scale_ is not None else np.ones(8)
    normalized = (risk_vector - mean) / scale

    logits = np.dot(model.weights_, normalized) + model.bias_
    exp_logits = np.exp(logits - np.max(logits))
    probs = exp_logits / np.sum(exp_logits)

    best_idx = int(np.argmax(probs))
    best_class = model.classes_[best_idx]
    best_weights = model.weights_[best_idx]

    attributions = {
        keys[i]: float(best_weights[i] * normalized[i])
        for i in range(8)
    }

    t1 = time.perf_counter()
    latency_ms = round((t1 - t0) * 1000, 2)

    return {
        "student_id": student_id,
        "attempt_count": attempt_count,
        "predicted_error": prediction.predicted_error if prediction else best_class,
        "probability": prediction.probability if prediction else float(probs[best_idx]),
        "confidence": prediction.confidence if prediction else float(probs[best_idx]) * min(1.0, attempt_count / 30.0),
        "status": prediction.status if prediction else ("NORMAL_OPERATION" if attempt_count >= 15 else "EARLY_SIGNAL"),
        "model_version": prediction.model_version if prediction else "MISTIQ-AMPA v1.0",
        "probabilities": {cls: round(float(probs[i]), 4) for i, cls in enumerate(model.classes_)},
        "logits": {cls: round(float(logits[i]), 4) for i, cls in enumerate(model.classes_)},
        "raw_features": {keys[i]: round(raw_vals[i], 3) for i in range(8)},
        "normalized_features": {keys[i]: round(float(normalized[i]), 3) for i in range(8)},
        "feature_attributions": {k: round(v, 4) for k, v in attributions.items()},
        "inference_latency_ms": latency_ms,
        "classes": list(model.classes_),
    }


@router.post("/predictions/simulate", summary="Run real-time inference on custom features or student personas")
def simulate_prediction(payload: SimulationRequest, ampa_service: AMPAService = Depends(get_ampa_service)):
    t0 = time.perf_counter()
    model = ampa_service.model
    if model is None or not model.fitted_:
        raise HTTPException(status_code=503, detail="Trained AMPA model is unavailable")

    PRESETS = {
        "concept_confused": {
            "mistake_frequency": 0.72, "mistake_recency": 0.88, "repetition_score": 0.65,
            "difficulty_sensitivity": 0.40, "behavior_pressure": 0.35, "concept_confusion": 0.92,
            "learning_stability": 0.30, "mistake_momentum": 0.45
        },
        "impulsive_rusher": {
            "mistake_frequency": 0.78, "mistake_recency": 0.70, "repetition_score": 0.50,
            "difficulty_sensitivity": 0.30, "behavior_pressure": 0.95, "concept_confusion": 0.20,
            "learning_stability": 0.25, "mistake_momentum": 0.30
        },
        "difficulty_wall": {
            "mistake_frequency": 0.60, "mistake_recency": 0.75, "repetition_score": 0.45,
            "difficulty_sensitivity": 0.94, "behavior_pressure": 0.40, "concept_confusion": 0.25,
            "learning_stability": 0.35, "mistake_momentum": 0.82
        },
        "procedure_flaw": {
            "mistake_frequency": 0.68, "mistake_recency": 0.60, "repetition_score": 0.85,
            "difficulty_sensitivity": 0.50, "behavior_pressure": 0.45, "concept_confusion": 0.30,
            "learning_stability": 0.40, "mistake_momentum": 0.20
        },
        "balanced_mastery": {
            "mistake_frequency": 0.12, "mistake_recency": 0.10, "repetition_score": 0.05,
            "difficulty_sensitivity": 0.15, "behavior_pressure": 0.10, "concept_confusion": 0.08,
            "learning_stability": 0.92, "mistake_momentum": -0.60
        }
    }

    raw = dict(PRESETS.get(payload.preset or "", PRESETS["concept_confused"]))
    if payload.features:
        raw.update(payload.features)

    keys = [
        "mistake_frequency", "mistake_recency", "repetition_score",
        "difficulty_sensitivity", "behavior_pressure", "concept_confusion",
        "learning_stability", "mistake_momentum"
    ]
    feature_vals = [float(raw.get(k, 0.5)) for k in keys]

    instability = 1.0 - feature_vals[6]
    risk_vector = np.array([
        feature_vals[0], feature_vals[1], feature_vals[2],
        feature_vals[3], feature_vals[4], feature_vals[5],
        instability, feature_vals[7]
    ], dtype=float)

    mean = model.feature_mean_ if model.feature_mean_ is not None else np.zeros(8)
    scale = model.feature_scale_ if model.feature_scale_ is not None else np.ones(8)
    normalized = (risk_vector - mean) / scale

    logits = np.dot(model.weights_, normalized) + model.bias_
    exp_logits = np.exp(logits - np.max(logits))
    probs = exp_logits / np.sum(exp_logits)

    best_idx = int(np.argmax(probs))
    best_class = model.classes_[best_idx]
    best_weights = model.weights_[best_idx]

    attributions = {
        keys[i]: float(best_weights[i] * normalized[i])
        for i in range(8)
    }

    t1 = time.perf_counter()
    latency_ms = round((t1 - t0) * 1000, 2)

    return {
        "predicted_error": best_class,
        "probability": float(probs[best_idx]),
        "confidence": float(probs[best_idx]) * min(1.0, payload.attempt_count / 30.0),
        "status": "NORMAL_OPERATION" if payload.attempt_count >= 15 else "EARLY_SIGNAL",
        "probabilities": {cls: round(float(probs[i]), 4) for i, cls in enumerate(model.classes_)},
        "logits": {cls: round(float(logits[i]), 4) for i, cls in enumerate(model.classes_)},
        "raw_features": {keys[i]: round(feature_vals[i], 3) for i in range(8)},
        "normalized_features": {keys[i]: round(float(normalized[i]), 3) for i in range(8)},
        "feature_attributions": {k: round(v, 4) for k, v in attributions.items()},
        "inference_latency_ms": latency_ms,
        "model_version": "MISTIQ-AMPA v1.0",
        "classes": list(model.classes_),
    }
