"""Application integration for the existing trained MISTIQ-AMPA artifact."""

from __future__ import annotations

from datetime import datetime, timezone
import logging
from pathlib import Path
from typing import Mapping

import numpy as np

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

try:
    from backend.ml.ampa import MISTIQAMPA
    from backend.ml.ampa.features import FEATURE_NAMES
    from backend.ml.ampa.model import MODEL_VERSION
except ModuleNotFoundError:
    from ml.ampa import MISTIQAMPA
    from ml.ampa.features import FEATURE_NAMES
    from ml.ampa.model import MODEL_VERSION
from app.core.error_types import ErrorType
from app.core.config import settings
from app.models import Attempt, LearnerState, MistakeEvent, Prediction, Question, Recommendation, Student
from app.schemas.entities import AttemptCreate
from app.services.errors import InvalidAttempt, InvalidFeatureVector, ModelUnavailable, QuestionNotFound, StudentNotFound

logger = logging.getLogger(__name__)


class AMPAService:
    def __init__(self, model_path: str | Path, model: MISTIQAMPA | None = None):
        self.model_path = Path(model_path)
        self.model = model
        self.available = model is not None

    def load_once(self):
        if self.model is not None:
            self.available = True
            return self.model
        if not self.model_path.is_file():
            self.available = False
            raise ModelUnavailable(f"Trained AMPA artifact not found: {self.model_path}")
        try:
            self.model = MISTIQAMPA().load(self.model_path)
        except Exception as error:
            self.available = False
            raise ModelUnavailable(f"Could not load trained AMPA artifact: {error}") from error
        self.available = True
        return self.model

    def hydrate(self, session_factory):
        """Restore per-student history once at startup; learned W/b stay unchanged."""
        if not self.available or self.model is None:
            return
        with session_factory() as session:
            rows = session.execute(
                select(Attempt, Question, MistakeEvent)
                .join(Question, Attempt.question_id == Question.question_id)
                .outerjoin(MistakeEvent, MistakeEvent.attempt_id == Attempt.attempt_id)
                .order_by(Attempt.student_id, Attempt.timestamp, Attempt.attempt_id)
        ).all()
        for attempt, question, mistake in rows:
            if not attempt.correct and mistake is None:
                raise ValueError(f"attempt {attempt.attempt_id} is incorrect but has no mistake event")
            self.model.update(_interaction(attempt, question, mistake))

    def submit_attempt(self, session: Session, payload: AttemptCreate):
        """Persist one attempt and all derived state atomically."""
        if not self.available or self.model is None:
            raise ModelUnavailable("No trained AMPA model is available; configure MISTIQ_AMPA_MODEL_PATH")
        if payload.idempotency_key:
            duplicate = session.scalar(select(Attempt).where(Attempt.idempotency_key == payload.idempotency_key))
            if duplicate:
                if (duplicate.student_id != payload.student_id or duplicate.question_id != payload.question_id
                        or duplicate.selected_option != payload.selected_option
                        or duplicate.response_time != payload.response_time):
                    raise InvalidAttempt("idempotency_key was already used for a different attempt")
                return self._submission_response(session, duplicate, "duplicate_request")
        student = session.get(Student, payload.student_id)
        if student is None:
            raise StudentNotFound(f"Student {payload.student_id} was not found")
        question = session.get(Question, payload.question_id)
        if question is None:
            raise QuestionNotFound(f"Question {payload.question_id} was not found")
        if payload.selected_option not in {"A", "B", "C", "D"} or not (0 < payload.response_time <= 900):
            raise InvalidAttempt("selected_option or response_time is invalid")

        previous_count = session.scalar(select(func.count(Attempt.attempt_id)).where(
            Attempt.student_id == student.id, Attempt.question_id == question.question_id
        )) or 0
        attempt = Attempt(
            student_id=student.id, question_id=question.question_id,
            selected_option=payload.selected_option,
            correct=payload.selected_option == question.correct_option,
            response_time=payload.response_time, timestamp=datetime.now(timezone.utc).replace(tzinfo=None),
            attempt_number=previous_count + 1, idempotency_key=payload.idempotency_key,
        )
        staged = False
        try:
            session.add(attempt)
            session.flush()
            mistake = None
            if not attempt.correct:
                error_type = self._classify_mistake(session, student.id, question, attempt)
                mistake = MistakeEvent(
                    student_id=student.id, attempt_id=attempt.attempt_id, error_type=error_type,
                    topic=question.topic, subtopic=question.subtopic, timestamp=attempt.timestamp,
                )
                session.add(mistake)
                session.flush()
            suggested = session.scalar(
                select(Recommendation).where(
                    Recommendation.student_id == student.id,
                    Recommendation.question_id == question.question_id,
                    Recommendation.completed_at.is_(None),
                ).order_by(Recommendation.created_at.desc(), Recommendation.id.desc())
            )
            if suggested is not None:
                from app.services.recommendation_service import complete_recommendation
                complete_recommendation(session, suggested)

            interaction = _interaction(attempt, question, mistake)
            self.model.update(interaction)
            staged = True
            state = self._update_learner_state(session, student.id)
            inference_time = datetime.now(timezone.utc)
            context = {"topic": question.topic, "subtopic": question.subtopic,
                       "difficulty": question.difficulty,
                       "as_of": inference_time.isoformat()}
            features = self.model.extract_student_features(student.id, context)
            if features.shape != (len(self.model.classes_), len(FEATURE_NAMES)):
                raise InvalidFeatureVector("AMPA feature matrix has an unexpected shape")
            attempt_count = session.scalar(select(func.count(Attempt.attempt_id)).where(Attempt.student_id == student.id)) or 0
            mistake_count = session.scalar(select(func.count(MistakeEvent.mistake_event_id)).where(MistakeEvent.student_id == student.id)) or 0
            _persist_state_features(state, features, attempt_count, mistake_count)

            # Reuse the same cutoff for features, prediction and explanation so
            # the stored research trace can be reproduced exactly.
            output = self.model.predict_for_student(student.id, context)
            prediction = None
            if output["predicted_error"] is not None:
                explanation = self.model.explain(student.id, context)
                trace_snapshot = _research_trace_snapshot(self.model, features, inference_time)
                prediction = Prediction(
                    student_id=student.id, predicted_error=ErrorType(output["predicted_error"]),
                    probability=output["probability"], confidence=output["confidence"],
                    data_reliability=output["data_reliability"], status=output["confidence_level"],
                    model_name="MISTIQ-AMPA", model_version=MODEL_VERSION,
                    context_question_id=question.question_id, source_attempt_id=attempt.attempt_id,
                    explanation={**_explanation_payload(explanation, output.get("probabilities", {})),
                                 "research_trace_snapshot": trace_snapshot},
                )
                session.add(prediction)
                session.flush()
            response = self._submission_response(session, attempt, output["confidence_level"],
                                                 mistake_override=mistake, prediction_override=prediction)
            session.commit()
            return response
        except Exception as error:
            session.rollback()
            if staged:
                self.model.student_state.discard_last(student.id, attempt.attempt_id)
            if isinstance(error, (InvalidAttempt, InvalidFeatureVector, ModelUnavailable)):
                raise
            logger.exception("Attempt transaction failed")
            raise

    def _classify_mistake(self, session, student_id, question, attempt):
        mapping = question.error_mapping or {}
        mapped = mapping.get(attempt.selected_option)
        try:
            mapped_type = ErrorType(mapped) if mapped else None
        except ValueError:
            mapped_type = None
        if mapped_type in (None, ErrorType.CORRECT):
            raise InvalidAttempt("question has no valid error mapping for the selected distractor")
        previous_same = session.scalar(
            select(func.count(Attempt.attempt_id))
            .join(MistakeEvent, MistakeEvent.attempt_id == Attempt.attempt_id)
            .where(
                MistakeEvent.student_id == student_id,
                Attempt.question_id == question.question_id,
                Attempt.selected_option == attempt.selected_option,
                or_(
                    Attempt.timestamp < attempt.timestamp,
                    and_(Attempt.timestamp == attempt.timestamp,
                         Attempt.attempt_id < attempt.attempt_id),
                ),
            )
        ) or 0
        estimated = max(1, question.estimated_time or 1)
        if attempt.response_time >= estimated * 1.5:
            return ErrorType.TIME_PRESSURE
        if question.difficulty >= 4 and attempt.response_time > estimated:
            return ErrorType.DIFFICULTY_FAILURE
        if previous_same:
            return ErrorType.REPEATED_MISTAKE
        return mapped_type

    def _update_learner_state(self, session, student_id):
        state = session.scalar(select(LearnerState).where(LearnerState.student_id == student_id))
        if state is None:
            state = LearnerState(student_id=student_id)
            session.add(state)
            session.flush()
        return state

    @staticmethod
    def _submission_response(session, attempt, status, mistake_override=None, prediction_override=None):
        from app.schemas.entities import AttemptSubmission, MistakeEvent as MistakeSchema, PredictionRead
        mistake = mistake_override if mistake_override is not None else attempt.mistake_event
        prediction = prediction_override or session.scalar(
            select(Prediction).where(Prediction.source_attempt_id == attempt.attempt_id)
        )
        prediction_data = None
        if prediction is not None:
            prediction_data = PredictionRead(
                id=prediction.id, student_id=prediction.student_id,
                prediction=prediction.predicted_error, probability=prediction.probability,
                confidence=prediction.confidence, reliability=prediction.data_reliability,
                status=prediction.status, model=prediction.model_name,
                model_version=prediction.model_version,
                context_question_id=prediction.context_question_id, timestamp=prediction.created_at,
                top_predictions=(prediction.explanation or {}).get("top_predictions", []),
            )
        return AttemptSubmission(
            attempt=attempt, mistake_event=MistakeSchema.model_validate(mistake) if mistake else None,
            prediction=prediction_data, prediction_status=status,
            correct_option=attempt.question.correct_option,
            correct_answer=getattr(attempt.question, f"option_{attempt.question.correct_option.lower()}"),
        )


def _interaction(attempt, question, mistake):
    return {
        "student_id": attempt.student_id, "attempt_id": attempt.attempt_id,
        "question_id": question.question_id, "topic": question.topic,
        "subtopic": question.subtopic, "difficulty": question.difficulty,
        "selected_option": attempt.selected_option, "correct": attempt.correct,
        "response_time": attempt.response_time,
        "timestamp": attempt.timestamp.isoformat() + ("Z" if attempt.timestamp.tzinfo is None else ""),
        "attempt_number": attempt.attempt_number,
        "error_type": mistake.error_type.value if mistake else ErrorType.CORRECT.value,
    }


def _persist_state_features(state, features, attempt_count, mistake_count):
    state.mistake_frequency = float(features[:, 0].max())
    state.mistake_recency = float(features[:, 1].max())
    state.repetition_score = float(features[:, 2].max())
    state.difficulty_sensitivity = float(features[:, 3].mean())
    state.behavior_pressure = float(features[:, 4].max())
    state.concept_confusion = float(features[:, 5].max())
    state.knowledge_stability = float(features[:, 6].mean())
    state.mistake_momentum = float(features[:, 7].mean())
    state.attempt_count = attempt_count
    state.relevant_mistake_count = mistake_count


def _explanation_payload(explanation: Mapping, probabilities=None):
    top_predictions = [{"error_type": label, "probability": float(value)}
                       for label, value in sorted((probabilities or {}).items(), key=lambda pair: (-pair[1], pair[0]))[:settings.prediction_top_k]]
    return {
        "prediction": explanation["prediction"], "probability": explanation["probability"],
        "risk_score": explanation["risk_score"],
        "reasons": [{"feature": reason["feature"], "value": reason["feature_value"],
                     "weight": reason["learned_weight"], "contribution": reason["contribution"]}
                    for reason in explanation["reasons"]],
        "top_predictions": top_predictions,
    }


def _research_trace_snapshot(model, raw_features, inference_time):
    """Persist exact inference operands for reproducible research traces."""
    try:
        from backend.ml.ampa.features import FEATURE_NAMES, RISK_FEATURE_NAMES
        from backend.ml.ampa.risk import class_risk, softmax
    except ModuleNotFoundError:
        from ml.ampa.features import FEATURE_NAMES, RISK_FEATURE_NAMES
        from ml.ampa.risk import class_risk, softmax

    scoring = np.array(raw_features, dtype=float, copy=True)
    scoring[:, 6] = 1.0 - scoring[:, 6]
    scoring = (scoring - model.feature_mean_) / model.feature_scale_
    scores = class_risk(scoring[None, :, :], model.weights_, model.bias_)[0]
    shifted = scores - np.max(scores)
    exponentials = np.exp(shifted)
    probabilities = softmax(scores)
    return {
        "raw_features_by_class": {label: {name: float(raw_features[c, i]) for i, name in enumerate(FEATURE_NAMES)}
                                  for c, label in enumerate(model.classes_)},
        "scoring_features_by_class": {label: {name: float(scoring[c, i]) for i, name in enumerate(RISK_FEATURE_NAMES)}
                                      for c, label in enumerate(model.classes_)},
        "weights": model.weights_.tolist(), "bias": model.bias_.tolist(),
        "feature_mean": model.feature_mean_.tolist(),
        "feature_scale": model.feature_scale_.tolist(),
        "configuration": model._configuration(),
        "inference_as_of": inference_time.isoformat(),
        "raw_scores": {label: float(scores[i]) for i, label in enumerate(model.classes_)},
        "shifted_scores": {label: float(shifted[i]) for i, label in enumerate(model.classes_)},
        "exponentials": {label: float(exponentials[i]) for i, label in enumerate(model.classes_)},
        "probabilities": {label: float(probabilities[i]) for i, label in enumerate(model.classes_)},
    }
