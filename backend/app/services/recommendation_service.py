"""History-grounded question ranking. Scores select practice; they are not predictions."""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import Attempt, MistakeEvent, Prediction, Question, Recommendation, Student


DEFAULT_WEIGHTS = {
    "learning_need": .35, "mistake_relevance": .25, "difficulty_fit": .20,
    "novelty": .10, "retention_value": .10,
}


class RecommendationService:
    def __init__(self, weights=None, concept_pairs=None):
        self.weights = dict(weights or settings.recommendation_weights or DEFAULT_WEIGHTS)
        self.concept_pairs = tuple(tuple(pair) for pair in (concept_pairs or settings.concept_confusion_pairs))
        if set(self.weights) != set(DEFAULT_WEIGHTS) or any(v < 0 for v in self.weights.values()) or sum(self.weights.values()) <= 0:
            raise ValueError("recommendation weights must be non-negative and include all five score components")
        total = sum(self.weights.values())
        self.weights = {key: value / total for key, value in self.weights.items()}

    def recommend_next(self, session: Session, student_id: int) -> Recommendation | None:
        student = session.get(Student, student_id)
        if student is None:
            return None
        pending = session.scalar(
            select(Recommendation).where(
                Recommendation.student_id == student_id,
                Recommendation.completed_at.is_(None),
                Recommendation.question_id.is_not(None),
            ).order_by(Recommendation.created_at.desc(), Recommendation.id.desc())
        )
        if pending is not None and session.get(Question, pending.question_id) is not None:
            return pending
        questions = session.scalars(select(Question).order_by(Question.question_id)).all()
        if not questions:
            return None
        attempts = session.scalars(select(Attempt).where(Attempt.student_id == student_id).order_by(Attempt.timestamp, Attempt.attempt_id)).all()
        mistakes = session.scalars(select(MistakeEvent).where(MistakeEvent.student_id == student_id).order_by(MistakeEvent.timestamp, MistakeEvent.mistake_event_id)).all()
        counts = Counter(attempt.question_id for attempt in attempts)
        latest_prediction = session.scalar(
            select(Prediction).where(Prediction.student_id == student_id)
            .order_by(Prediction.created_at.desc(), Prediction.id.desc())
        )
        reliable_prediction = latest_prediction is not None and latest_prediction.status == "NORMAL_OPERATION"
        unseen = [question for question in questions if counts[question.question_id] == 0]
        if unseen:
            questions = unseen
        if not reliable_prediction:
            # During AMPA cold start, offer deterministic, not personalized practice.
            question = min(questions, key=lambda item: (counts[item.question_id], item.question_id))
            recommendation = Recommendation(
                student_id=student_id, prediction_id=None, question_id=question.question_id,
                type="STARTER_PRACTICE",
                reason="A starter question while MISTIQ gathers enough practice history for a reliable prediction.",
                score=None, score_components=None, created_at=datetime.now(timezone.utc),
            )
            session.add(recommendation)
            session.flush()
            return recommendation
        recent_mistakes = mistakes[-20:]
        question_by_id = {question.question_id: question for question in questions}
        success_by_difficulty: dict[int, list[bool]] = {}
        for attempt in attempts:
            question = question_by_id.get(attempt.question_id)
            if question:
                success_by_difficulty.setdefault(question.difficulty, []).append(attempt.correct)
        observed = {difficulty: sum(values) / len(values) for difficulty, values in success_by_difficulty.items()}
        target_difficulty = max(observed, key=lambda level: (observed[level], -level)) if observed else 2
        ranked = []
        for question in questions:
            matching = [m for m in recent_mistakes if m.topic == question.topic]
            exact = [m for m in matching if question.subtopic and m.subtopic == question.subtopic]
            concept = question.subtopic or question.topic
            paired = [m for m in recent_mistakes if any(
                {concept.casefold(), (m.subtopic or m.topic).casefold()} == {left.casefold(), right.casefold()}
                for left, right in self.concept_pairs
            )]
            errors = len(matching)
            learning_need = min(1.0, (len(exact) * 1.0 + len(paired) * .75 + max(0, errors - len(exact)) * .45) / 3)
            mistake_relevance = min(1.0, (len(exact) * 1.0 + len(paired) * .75 + len(matching) * .35) / 3)
            difficulty_fit = max(0.0, 1.0 - abs(question.difficulty - target_difficulty) / 4)
            novelty = 1.0 / (1.0 + counts[question.question_id])
            retention_value = min(1.0, (len(exact) + len(paired) * .75 + errors * .25) / 3)
            components = {"learning_need": learning_need, "mistake_relevance": mistake_relevance,
                          "difficulty_fit": difficulty_fit, "novelty": novelty,
                          "retention_value": retention_value}
            score = sum(components[key] * self.weights[key] for key in components)
            # Stable tie-breaking gives reproducible selection from the same DB snapshot.
            ranked.append((score, -counts[question.question_id], -question.question_id, question, components))
        score, _, _, question, components = max(ranked, key=lambda row: row[:3])
        reasons = sorted(components.items(), key=lambda item: item[1] * self.weights[item[0]], reverse=True)
        strongest = reasons[0][0]
        reason_copy = {
            "learning_need": f"This {question.subtopic or question.topic} question addresses a topic where your recent practice shows room to review.",
            "mistake_relevance": f"This question is related to {question.subtopic or question.topic}, which appears in your recent review history.",
            "difficulty_fit": f"This question is at difficulty {question.difficulty}, near the level supported by your practice history.",
            "novelty": "This question gives you a fresh opportunity to practice.",
            "retention_value": f"A new question on {question.subtopic or question.topic} can help you revisit this topic.",
        }
        recommendation = Recommendation(
            student_id=student_id, prediction_id=latest_prediction.id if latest_prediction else None,
            question_id=question.question_id, type="PRACTICE_QUESTION", score=score,
            score_components=components, reason=reason_copy[strongest], created_at=datetime.now(timezone.utc),
        )
        session.add(recommendation)
        session.flush()
        return recommendation


def complete_recommendation(session: Session, recommendation: Recommendation) -> Recommendation:
    if recommendation.completed_at is None:
        recommendation.completed_at = datetime.now(timezone.utc)
    return recommendation
