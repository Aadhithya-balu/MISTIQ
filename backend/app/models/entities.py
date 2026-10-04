from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, Enum, Float, ForeignKey, Integer, JSON, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.core.error_types import ErrorType


class Student(Base):
    __tablename__ = "students"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    attempts: Mapped[list["Attempt"]] = relationship(back_populates="student", cascade="all, delete-orphan")
    learner_state: Mapped["LearnerState | None"] = relationship(back_populates="student", cascade="all, delete-orphan", uselist=False)
    predictions: Mapped[list["Prediction"]] = relationship(back_populates="student", cascade="all, delete-orphan")
    recommendations: Mapped[list["Recommendation"]] = relationship(back_populates="student", cascade="all, delete-orphan")


class Question(Base):
    __tablename__ = "questions"
    __table_args__ = (
        CheckConstraint("difficulty BETWEEN 1 AND 5", name="ck_questions_difficulty"),
        CheckConstraint("estimated_time > 0", name="ck_questions_estimated_time"),
    )
    question_id: Mapped[int] = mapped_column(primary_key=True)
    topic: Mapped[str] = mapped_column(String(200), nullable=False)
    subtopic: Mapped[str | None] = mapped_column(String(200))
    difficulty: Mapped[int] = mapped_column(Integer, nullable=False)
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    option_a: Mapped[str] = mapped_column(Text, nullable=False)
    option_b: Mapped[str] = mapped_column(Text, nullable=False)
    option_c: Mapped[str] = mapped_column(Text, nullable=False)
    option_d: Mapped[str] = mapped_column(Text, nullable=False)
    correct_option: Mapped[str] = mapped_column(String(1), nullable=False)
    estimated_time: Mapped[int] = mapped_column(Integer, nullable=False)
    error_mapping: Mapped[dict[str, str]] = mapped_column(JSON, nullable=False, default=dict)
    attempts: Mapped[list["Attempt"]] = relationship(back_populates="question")


class Attempt(Base):
    __tablename__ = "attempts"
    __table_args__ = (
        CheckConstraint("response_time > 0", name="ck_attempts_response_time"),
        CheckConstraint("attempt_number >= 1", name="ck_attempts_attempt_number"),
        CheckConstraint("selected_option IN ('A', 'B', 'C', 'D')", name="ck_attempts_selected_option"),
        UniqueConstraint("student_id", "question_id", "attempt_number", name="uq_attempt_student_question_number"),
    )
    attempt_id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), nullable=False)
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.question_id"), nullable=False)
    selected_option: Mapped[str] = mapped_column(String(1), nullable=False)
    correct: Mapped[bool] = mapped_column(Boolean, nullable=False)
    response_time: Mapped[float] = mapped_column(Float, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    attempt_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    idempotency_key: Mapped[str | None] = mapped_column(String(100), unique=True)
    student: Mapped[Student] = relationship(back_populates="attempts")
    question: Mapped[Question] = relationship(back_populates="attempts")
    mistake_event: Mapped["MistakeEvent | None"] = relationship(back_populates="attempt", cascade="all, delete-orphan", uselist=False)


class MistakeEvent(Base):
    __tablename__ = "mistake_events"
    __table_args__ = (UniqueConstraint("attempt_id", name="uq_mistake_attempt"),)
    mistake_event_id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), nullable=False)
    attempt_id: Mapped[int] = mapped_column(ForeignKey("attempts.attempt_id"), nullable=False)
    error_type: Mapped[ErrorType] = mapped_column(Enum(ErrorType, native_enum=False), nullable=False)
    topic: Mapped[str] = mapped_column(String(200), nullable=False)
    subtopic: Mapped[str | None] = mapped_column(String(200))
    timestamp: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    attempt: Mapped[Attempt] = relationship(back_populates="mistake_event")


class LearnerState(Base):
    __tablename__ = "learner_states"
    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), unique=True, nullable=False)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    relevant_mistake_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    mistake_frequency: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    mistake_recency: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    repetition_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    difficulty_sensitivity: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    behavior_pressure: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    concept_confusion: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    knowledge_stability: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    mistake_momentum: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    student: Mapped[Student] = relationship(back_populates="learner_state")


class Prediction(Base):
    __tablename__ = "predictions"
    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), nullable=False)
    predicted_error: Mapped[str] = mapped_column(String(40), nullable=False)
    probability: Mapped[float] = mapped_column(Float, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    data_reliability: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    model_version: Mapped[str] = mapped_column(String(40), nullable=False)
    context_question_id: Mapped[int | None] = mapped_column(ForeignKey("questions.question_id"))
    source_attempt_id: Mapped[int | None] = mapped_column(ForeignKey("attempts.attempt_id"), unique=True)
    explanation: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    student: Mapped[Student] = relationship(back_populates="predictions")
    context_question: Mapped[Question | None] = relationship()
    recommendations: Mapped[list["Recommendation"]] = relationship(back_populates="prediction")


class Recommendation(Base):
    __tablename__ = "recommendations"
    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), nullable=False)
    prediction_id: Mapped[int | None] = mapped_column(ForeignKey("predictions.id"))
    type: Mapped[str] = mapped_column(String(100), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    question_id: Mapped[int | None] = mapped_column(ForeignKey("questions.question_id"))
    score: Mapped[float | None] = mapped_column(Float)
    score_components: Mapped[dict | None] = mapped_column(JSON)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    student: Mapped[Student] = relationship(back_populates="recommendations")
    prediction: Mapped[Prediction | None] = relationship(back_populates="recommendations")
    question: Mapped[Question | None] = relationship()
