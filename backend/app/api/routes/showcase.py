from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies import get_ampa_service, get_db
from app.services.ampa_service import AMPAService
from app.services import showcase_service

router = APIRouter(prefix="/showcase", tags=["showcase"])


@router.get("/status", summary="Showcase demo student status")
def showcase_status(session: Session = Depends(get_db)):
    return showcase_service.demo_status(session)


@router.post("/reset", summary="Reset the showcase demo student's practice history")
def showcase_reset(session: Session = Depends(get_db),
                   ampa_service: AMPAService = Depends(get_ampa_service)):
    showcase_service.reset_demo_student(session, ampa_service)
    return {"reset": True, "student_id": showcase_service.DEMO_STUDENT_ID,
            "student_name": showcase_service.DEMO_STUDENT_NAME}


@router.post("/seed", summary="Seed the showcase demo student through the live AMPA pipeline")
def showcase_seed(session: Session = Depends(get_db),
                  ampa_service: AMPAService = Depends(get_ampa_service)):
    showcase_service.get_or_create_demo_student(session)
    showcase_service.reset_demo_student(session, ampa_service)
    showcase_service.ensure_curated_questions(session)
    return showcase_service.seed_demo_history(session, ampa_service)