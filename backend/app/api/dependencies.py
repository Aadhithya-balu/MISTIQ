from fastapi import Depends, Header, Request

from app.core.config import settings
from app.models import Recommendation, User
from app.schemas.entities import AttemptCreate
from app.services import auth_service
from app.services.errors import Forbidden, NotAuthenticated


def get_db(request: Request):
    session = request.app.state.SessionLocal()
    try:
        yield session
    finally:
        session.close()


def get_ampa_service(request: Request):
    service = request.app.state.ampa_service
    if service is None or not service.available:
        from app.services.errors import ModelUnavailable
        raise ModelUnavailable("Trained AMPA model unavailable; configure MISTIQ_AMPA_MODEL_PATH")
    return service


def get_current_user(authorization: str | None = Header(default=None), session=Depends(get_db)) -> User:
    """Resolve the signed-in account from the ``Authorization: Bearer`` token."""
    if not authorization or not authorization.lower().startswith("bearer "):
        raise NotAuthenticated("Please sign in to continue.")
    token = authorization.split(" ", 1)[1].strip()
    if not token:
        raise NotAuthenticated("Please sign in to continue.")
    user = auth_service.resolve_session(session, token)
    if user is None:
        raise NotAuthenticated("Your session has ended. Please sign in again.")
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    """Only the operator (admin) account may reach research/data endpoints."""
    if user.role != auth_service.ROLE_ADMIN:
        raise Forbidden("This area is restricted to administrators.")
    return user


def authorize_student(student_id: int, user: User = Depends(get_current_user)) -> User:
    """Students may only read their own record; admins may read any record."""
    if user.role != auth_service.ROLE_ADMIN and user.student_id != student_id:
        raise Forbidden("You can only access your own learning data.")
    return user


def authorize_attempt(payload: AttemptCreate, user: User = Depends(get_current_user)) -> User:
    if user.role != auth_service.ROLE_ADMIN and user.student_id != payload.student_id:
        raise Forbidden("You can only submit practice for your own profile.")
    return user


def authorize_recommendation(recommendation_id: int, user: User = Depends(get_current_user),
                             session=Depends(get_db)) -> User:
    recommendation = session.get(Recommendation, recommendation_id)
    if recommendation is not None and user.role != auth_service.ROLE_ADMIN and user.student_id != recommendation.student_id:
        raise Forbidden("You can only update your own recommendations.")
    return user


def session_ttl_hours() -> int:
    return settings.session_ttl_hours
