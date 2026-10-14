from fastapi import APIRouter, Depends

from app.api.dependencies import get_current_user, require_admin
from app.api.routes import attempts, questions, students
from app.api.routes import predictions, progress, health, recommendations
from app.api.routes import research, showcase, auth

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(students.router, tags=["students"], dependencies=[Depends(get_current_user)])
api_router.include_router(questions.router, tags=["questions"], dependencies=[Depends(get_current_user)])
api_router.include_router(attempts.router, tags=["attempts"], dependencies=[Depends(get_current_user)])
api_router.include_router(predictions.router, tags=["predictions"], dependencies=[Depends(get_current_user)])
api_router.include_router(recommendations.router, tags=["recommendations"], dependencies=[Depends(get_current_user)])
api_router.include_router(progress.router, tags=["progress"], dependencies=[Depends(get_current_user)])
api_router.include_router(health.router, tags=["health"])
api_router.include_router(research.router, dependencies=[Depends(require_admin)])
api_router.include_router(showcase.router, dependencies=[Depends(require_admin)])
