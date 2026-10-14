from fastapi import APIRouter, Depends, Header

from app.api.dependencies import get_current_user, get_db
from app.core.config import settings
from app.models import User
from app.schemas.auth import AuthResponse, AuthUser, LoginRequest, RegisterRequest
from app.services import auth_service
from app.services.errors import InvalidCredentials

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=AuthResponse, status_code=201,
             summary="Create a student account and start a session")
def register(payload: RegisterRequest, session=Depends(get_db)):
    user = auth_service.register_student(session, payload.name, payload.username, payload.password)
    token = auth_service.create_session(session, user, settings.session_ttl_hours)
    return auth_service.auth_response(session, user, token)


@router.post("/login", response_model=AuthResponse, summary="Sign in with username and password")
def login(payload: LoginRequest, session=Depends(get_db)):
    user = auth_service.authenticate(session, payload.username, payload.password)
    if user is None:
        raise InvalidCredentials("Incorrect username or password.")
    token = auth_service.create_session(session, user, settings.session_ttl_hours)
    return auth_service.auth_response(session, user, token)


@router.get("/me", response_model=AuthUser, summary="Return the signed-in account")
def me(user: User = Depends(get_current_user), session=Depends(get_db)):
    return auth_service.user_view(session, user)


@router.post("/logout", summary="End the current session")
def logout(authorization: str | None = Header(default=None), session=Depends(get_db)):
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()
        if token:
            auth_service.revoke_session(session, token)
    return {"status": "signed_out"}
