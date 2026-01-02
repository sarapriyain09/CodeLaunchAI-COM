from __future__ import annotations

from pydantic import BaseModel, Field


class GoogleAuthRequest(BaseModel):
    id_token: str = Field(min_length=20)


class GuestAuthRequest(BaseModel):
    email: str = Field(min_length=5)
    name: str | None = Field(default=None, max_length=120)


class UserPublic(BaseModel):
    id: str
    email: str
    name: str | None = None
    picture: str | None = None


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserPublic
