"""Account, session, and role logic for MISTIQ sign-in."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.security import hash_password, hash_token, new_token, verify_password
from app.models import AuthSession, Student, User
from app.services.errors import UsernameTaken

ROLE_STUDENT = "student"
ROLE_ADMIN = "admin"

USERNAME_MIN = 3
USERNAME_MAX = 100


def normalize_username(username: str) -> str:
    return username.strip().lower()


def _utcnow() -> datetime:
    """Naive UTC timestamp, portable across SQLite and Postgres columns."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def get_user_by_username(session: Session, username: str) -> User | None:
    return session.scalar(select(User).where(func.lower(User.username) == normalize_username(username)))


def create_user(session: Session, username: str, password: str, role: str, student_id: int | None = None) -> User:
    normalized = normalize_username(username)
    if not normalized:
        raise UsernameTaken("Please choose a username.")
    if get_user_by_username(session, normalized) is not None:
        raise UsernameTaken("That username is already taken.")
    user = User(username=normalized, password_hash=hash_password(password), role=role, student_id=student_id)
    session.add(user)
    session.flush()
    return user


def register_student(session: Session, name: str, username: str, password: str) -> User:
    student = Student(name=name.strip())
    session.add(student)
    session.flush()
    user = create_user(session, username, password, ROLE_STUDENT, student_id=student.id)
    session.commit()
    session.refresh(user)
    return user


def authenticate(session: Session, username: str, password: str) -> User | None:
    user = get_user_by_username(session, username)
    if user is None or not verify_password(password, user.password_hash):
        return None
    return user


def create_session(session: Session, user: User, ttl_hours: int) -> str:
    token = new_token()
    session.add(AuthSession(token_hash=hash_token(token), user_id=user.id,
                            expires_at=_utcnow() + timedelta(hours=ttl_hours)))
    session.commit()
    return token


def resolve_session(session: Session, token: str) -> User | None:
    row = session.scalar(select(AuthSession).where(AuthSession.token_hash == hash_token(token)))
    if row is None:
        return None
    if row.expires_at < _utcnow():
        session.delete(row)
        session.commit()
        return None
    return session.get(User, row.user_id)


def revoke_session(session: Session, token: str) -> None:
    row = session.scalar(select(AuthSession).where(AuthSession.token_hash == hash_token(token)))
    if row is not None:
        session.delete(row)
        session.commit()


def ensure_admin(session: Session, username: str, password: str) -> User:
    """Idempotently create the operator account used for the Research Lab."""
    existing = get_user_by_username(session, username)
    if existing is not None:
        if existing.role != ROLE_ADMIN:
            existing.role = ROLE_ADMIN
            session.commit()
        return existing
    admin = User(username=normalize_username(username), password_hash=hash_password(password),
                 role=ROLE_ADMIN, student_id=None)
    session.add(admin)
    session.commit()
    session.refresh(admin)
    return admin


def ensure_demo_student(session: Session, username: str, password: str, student_id: int = 1) -> User:
    """Idempotently create or update a demo student account linked to Student 1."""
    existing = get_user_by_username(session, username)
    if existing is not None:
        updated = False
        if existing.role != ROLE_STUDENT:
            existing.role = ROLE_STUDENT
            updated = True
        if existing.student_id != student_id:
            existing.student_id = student_id
            updated = True
        if updated:
            session.commit()
            session.refresh(existing)
        return existing
    user = User(username=normalize_username(username), password_hash=hash_password(password),
                role=ROLE_STUDENT, student_id=student_id)
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def user_view(session: Session, user: User) -> dict:
    name = None
    if user.student_id is not None:
        student = session.get(Student, user.student_id)
        name = student.name if student is not None else None
    return {"id": user.id, "username": user.username, "role": user.role,
            "name": name, "student_id": user.student_id}


def auth_response(session: Session, user: User, token: str) -> dict:
    return {"token": token, "user": user_view(session, user)}
