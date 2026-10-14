from typing import Literal

from pydantic import Field, field_validator

from app.schemas.entities import APIModel


class RegisterRequest(APIModel):
    model_config = {"extra": "forbid"}
    name: str = Field(min_length=1, max_length=200)
    username: str = Field(min_length=3, max_length=100)
    password: str = Field(min_length=6, max_length=200)

    @field_validator("name", "username")
    @classmethod
    def strip_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("cannot be blank")
        return value


class LoginRequest(APIModel):
    model_config = {"extra": "forbid"}
    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1, max_length=200)


class AuthUser(APIModel):
    id: int
    username: str
    role: Literal["student", "admin"]
    name: str | None = None
    student_id: int | None = None


class AuthResponse(APIModel):
    token: str
    user: AuthUser
