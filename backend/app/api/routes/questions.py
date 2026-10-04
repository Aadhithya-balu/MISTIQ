from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.models import Question
from app.schemas.entities import ErrorResponse, QuestionRead
from app.services.errors import QuestionNotFound

router = APIRouter()


@router.get("/questions", response_model=list[QuestionRead], summary="List questions")
def get_questions(topic: str | None = None, subtopic: str | None = None,
                  difficulty: int | None = Query(default=None, ge=1, le=5),
                  session: Session = Depends(get_db)):
    statement = select(Question).order_by(Question.question_id)
    if topic is not None:
        statement = statement.where(Question.topic == topic)
    if subtopic is not None:
        statement = statement.where(Question.subtopic == subtopic)
    if difficulty is not None:
        statement = statement.where(Question.difficulty == difficulty)
    return list(session.scalars(statement))


@router.get("/questions/{question_id}", response_model=QuestionRead, summary="Retrieve a question",
            responses={404: {"model": ErrorResponse, "description": "Question not found"}})
def get_question(question_id: int, session: Session = Depends(get_db)):
    question = session.get(Question, question_id)
    if question is None:
        raise QuestionNotFound(f"Question {question_id} was not found")
    return question
