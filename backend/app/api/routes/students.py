from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.models import Student
from app.schemas.entities import ErrorResponse, MistakeAnalyticsRead, MistakeEvent as MistakeRead, Student as StudentRead, StudentCreate
from app.services.errors import StudentNotFound
from app.services.analytics_data import load_student_history
from app.services.mistake_analytics_service import build_mistake_analytics

router = APIRouter()


@router.post("/students", response_model=StudentRead, status_code=201, summary="Create a student")
def create_student(payload: StudentCreate, session: Session = Depends(get_db)):
    student = Student(name=payload.name)
    session.add(student)
    session.commit()
    session.refresh(student)
    return student


@router.get("/students/{student_id}", response_model=StudentRead, summary="Retrieve a student",
            responses={404: {"model": ErrorResponse, "description": "Student not found"}})
def get_student(student_id: int, session: Session = Depends(get_db)):
    student = session.get(Student, student_id)
    if student is None:
        raise StudentNotFound(f"Student {student_id} was not found")
    return student


@router.get("/students/{student_id}/mistakes", response_model=list[MistakeRead], summary="List a student's mistake events",
            responses={404: {"model": ErrorResponse, "description": "Student not found"}})
def get_mistakes(student_id: int, session: Session = Depends(get_db)):
    if session.get(Student, student_id) is None:
        raise StudentNotFound(f"Student {student_id} was not found")
    history = load_student_history(session, student_id)
    return [MistakeRead(mistake_event_id=row["mistake_event_id"], student_id=student_id,
                        attempt_id=row["attempt_id"], error_type=row["error_type"],
                        topic=row["topic"], subtopic=row["subtopic"], timestamp=row["mistake_timestamp"])
            for row in history if row["mistake_event_id"] is not None]


def _mistake_analytics(student_id: int, session: Session):
    if session.get(Student, student_id) is None:
        raise StudentNotFound(f"Student {student_id} was not found")
    return build_mistake_analytics(load_student_history(session, student_id), student_id)


@router.get("/mistakes/{student_id}", response_model=list[MistakeRead], summary="List a student's mistakes")
def list_mistakes(student_id: int, session: Session = Depends(get_db)):
    return get_mistakes(student_id, session)


@router.get("/mistakes/{student_id}/summary", response_model=MistakeAnalyticsRead,
            summary="Summarize mistake types and frequency")
def get_mistake_summary(student_id: int, session: Session = Depends(get_db)):
    return _mistake_analytics(student_id, session)


@router.get("/mistakes/{student_id}/repeated", summary="List repeated mistake patterns")
def get_repeated_mistakes(student_id: int, session: Session = Depends(get_db)):
    return _mistake_analytics(student_id, session)["repeated"]


@router.get("/mistakes/{student_id}/confusions", summary="Return observed concept confusion pairs")
def get_concept_confusions(student_id: int, session: Session = Depends(get_db)):
    return _mistake_analytics(student_id, session)["confusions"]
