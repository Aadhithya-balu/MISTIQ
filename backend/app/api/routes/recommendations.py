from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.models import Recommendation, Student
from app.schemas.entities import ErrorResponse, RecommendedPractice, Recommendation as RecommendationSchema
from app.services.errors import RecommendationNotFound, RecommendationUnavailable, StudentNotFound
from app.services.recommendation_service import RecommendationService, complete_recommendation

router = APIRouter()
service = RecommendationService()


@router.get("/recommendations/{student_id}", response_model=list[RecommendationSchema])
def get_recommendations(student_id: int, session: Session = Depends(get_db)):
    if session.get(Student, student_id) is None:
        raise StudentNotFound(f"Student {student_id} was not found")
    return session.scalars(select(Recommendation).where(Recommendation.student_id == student_id)
                           .order_by(Recommendation.created_at.desc(), Recommendation.id.desc())).all()


@router.get("/recommendations/{student_id}/next", response_model=RecommendedPractice,
            responses={404: {"model": ErrorResponse, "description": "Student or question not found"}})
def get_next_recommendation(student_id: int, session: Session = Depends(get_db)):
    if session.get(Student, student_id) is None:
        raise StudentNotFound(f"Student {student_id} was not found")
    recommendation = service.recommend_next(session, student_id)
    if recommendation is None:
        raise RecommendationUnavailable("No practice questions are available yet")
    question = recommendation.question
    cold_start = recommendation.type == "STARTER_PRACTICE"
    session.commit()
    return {"recommendation": recommendation, "question": question, "cold_start": cold_start}


@router.post("/recommendations/{recommendation_id}/complete", response_model=RecommendationSchema)
def mark_recommendation_complete(recommendation_id: int, session: Session = Depends(get_db)):
    recommendation = session.get(Recommendation, recommendation_id)
    if recommendation is None:
        raise RecommendationNotFound(f"Recommendation {recommendation_id} was not found")
    complete_recommendation(session, recommendation)
    session.commit()
    session.refresh(recommendation)
    return recommendation
