from __future__ import annotations

from pydantic import BaseModel, Field


class GoogleAuthRequest(BaseModel):
    id_token: str = Field(min_length=20)


class GuestAuthRequest(BaseModel):
    email: str = Field(min_length=5)
    name: str | None = Field(default=None, max_length=120)


class EmailPasswordLoginRequest(BaseModel):
    email: str = Field(min_length=5)
    password: str = Field(min_length=8, max_length=256)


class EmailPasswordRegisterRequest(BaseModel):
    first_name: str = Field(min_length=1, max_length=80)
    last_name: str = Field(min_length=1, max_length=80)
    email: str = Field(min_length=5)
    password: str = Field(min_length=8, max_length=256)


class UserPublic(BaseModel):
    id: str
    email: str
    name: str | None = None
    picture: str | None = None


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserPublic
