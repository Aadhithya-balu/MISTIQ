from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies import get_ampa_service, get_db
from app.schemas.entities import AttemptCreate, AttemptSubmission, ErrorResponse
from app.services.ampa_service import AMPAService

router = APIRouter()


@router.post("/attempts", response_model=AttemptSubmission, status_code=201,
             summary="Submit an answer attempt", description="Correctness is computed from the stored question answer key.",
             responses={
                 404: {"model": ErrorResponse, "description": "Student or question not found"},
                 422: {"model": ErrorResponse, "description": "Invalid attempt or feature vector"},
                 503: {"model": ErrorResponse, "description": "Trained AMPA model unavailable"},
             })
def create_attempt(payload: AttemptCreate, session: Session = Depends(get_db),
                   ampa_service: AMPAService = Depends(get_ampa_service)):
    return ampa_service.submit_attempt(session, payload)
