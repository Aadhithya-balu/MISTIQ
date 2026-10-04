from datetime import datetime
from typing import Literal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

from app.core.time import utc_isoformat
from app.schemas.common import ErrorType


class APIModel(BaseModel):
    @field_serializer("*", check_fields=False, when_used="json", return_type=Any)
    def serialize_datetimes_as_utc(self, value):
        return utc_isoformat(value) if isinstance(value, datetime) else value


class Student(APIModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    created_at: datetime


class Question(APIModel):
    model_config = ConfigDict(from_attributes=True)
    question_id: int
    topic: str
    subtopic: str | None = None
    difficulty: int = Field(ge=1, le=5)
    question_text: str
    option_a: str
    option_b: str
    option_c: str
    option_d: str
    correct_option: str
    estimated_time: int
    error_mapping: dict[str, ErrorType]


class Attempt(APIModel):
    model_config = ConfigDict(from_attributes=True)
    attempt_id: int
    student_id: int
    question_id: int
    selected_option: str
    correct: bool
    response_time: float
    timestamp: datetime
    attempt_number: int


class MistakeEvent(APIModel):
    model_config = ConfigDict(from_attributes=True)
    mistake_event_id: int
    student_id: int
    attempt_id: int
    error_type: ErrorType
    topic: str
    subtopic: str | None = None
    timestamp: datetime


class LearnerState(APIModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    student_id: int
    updated_at: datetime
    mistake_frequency: float
    mistake_recency: float
    repetition_score: float
    difficulty_sensitivity: float
    behavior_pressure: float
    concept_confusion: float
    knowledge_stability: float
    mistake_momentum: float
    attempt_count: int = 0
    relevant_mistake_count: int = 0


class Prediction(APIModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    student_id: int
    predicted_error: ErrorType
    probability: float
    confidence: float
    data_reliability: float
    status: str
    model_name: str
    model_version: str
    context_question_id: int | None = None
    source_attempt_id: int | None = None
    explanation: dict | None = None
    created_at: datetime


class Recommendation(APIModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    student_id: int
    type: str
    reason: str
    created_at: datetime
    question_id: int | None = None
    score: float | None = None
    score_components: dict[str, float] | None = None
    completed_at: datetime | None = None


class StudentCreate(APIModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=200)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value):
        value = value.strip()
        if not value:
            raise ValueError("name cannot be blank")
        return value


class QuestionRead(APIModel):
    """Public question view omits the answer key and error mapping."""
    model_config = ConfigDict(from_attributes=True)
    question_id: int
    topic: str
    subtopic: str | None
    difficulty: int = Field(ge=1, le=5)
    question_text: str
    option_a: str
    option_b: str
    option_c: str
    option_d: str
    estimated_time: int


class RecommendedPractice(APIModel):
    recommendation: Recommendation
    question: QuestionRead
    cold_start: bool = False


class AttemptCreate(APIModel):
    model_config = ConfigDict(extra="forbid")
    student_id: int = Field(gt=0)
    question_id: int = Field(gt=0)
    selected_option: Literal["A", "B", "C", "D"]
    response_time: float = Field(gt=0, le=900)
    idempotency_key: str | None = Field(default=None, min_length=1, max_length=100)


class PredictionRead(APIModel):
    id: int
    student_id: int
    prediction: ErrorType
    probability: float
    confidence: float
    reliability: float
    status: str
    model: str
    model_version: str
    context_question_id: int | None
    timestamp: datetime
    top_predictions: list[dict] = Field(default_factory=list)


class PredictionExplanation(APIModel):
    prediction: ErrorType
    probability: float
    risk_score: float
    reasons: list[dict]
    top_predictions: list[dict] = Field(default_factory=list)
    summary: str | None = None
    evidence: list[str] = Field(default_factory=list)
    learning_need: list[str] = Field(default_factory=list)


class AttemptSubmission(APIModel):
    attempt: Attempt
    mistake_event: MistakeEvent | None
    prediction: PredictionRead | None
    prediction_status: str
    correct_option: Literal["A", "B", "C", "D"]
    correct_answer: str


class ProgressRead(APIModel):
    student_id: int
    attempt_count: int
    correct_count: int
    accuracy: float
    mistake_count: int
    summary: dict = Field(default_factory=dict)
    topic_performance: list[dict] = Field(default_factory=list)
    subtopic_performance: list[dict] = Field(default_factory=list)
    difficulty_performance: list[dict] = Field(default_factory=list)
    trajectory: list[dict] = Field(default_factory=list)
    difficulty_trajectory: list[dict] = Field(default_factory=list)
    recovery: dict = Field(default_factory=dict)
    stability: dict = Field(default_factory=dict)
    mistake_momentum: dict = Field(default_factory=dict)


class MistakeAnalyticsRead(APIModel):
    student_id: int
    mistake_count: int
    attempt_count: int
    distribution: list[dict]
    recent_frequency: float | None
    trend: str
    timeline_bucket: Literal["daily", "weekly"]
    timeline: list[dict]
    timeline_sufficient: bool
    timeline_message: str | None
    repeated: list[dict]
    confusions: dict
    recent_mistakes: list[MistakeEvent]


class ErrorResponse(APIModel):
    error: str
    detail: str
