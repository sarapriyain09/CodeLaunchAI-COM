from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from app.schemas.auth import (
    AuthResponse,
    EmailPasswordLoginRequest,
    EmailPasswordRegisterRequest,
    GoogleAuthRequest,
    GuestAuthRequest,
    UserPublic,
)
from app.services.auth import issue_access_token, require_user, verify_google_id_token
from app.services.credentials_store import register_email_password, verify_email_password
from app.services.user_store import get_user
from app.services.user_store import upsert_user_from_email, upsert_user_from_google


router = APIRouter()


@router.post("/auth/google", response_model=AuthResponse)
async def auth_google(body: GoogleAuthRequest) -> AuthResponse:
    claims = await verify_google_id_token(body.id_token)

    user = upsert_user_from_google(
        sub=str(claims.get("sub")),
        email=str(claims.get("email")),
        name=claims.get("name"),
        picture=claims.get("picture"),
    )

    access_token = issue_access_token(
        user_id=user["id"],
        email=user["email"],
        name=user.get("name"),
    )

    return AuthResponse(
        access_token=access_token,
        user=UserPublic(
            id=user["id"],
            email=user["email"],
            name=user.get("name"),
            picture=user.get("picture"),
        ),
    )


@router.post("/auth/guest", response_model=AuthResponse)
async def auth_guest(body: GuestAuthRequest) -> AuthResponse:
    try:
        user = upsert_user_from_email(email=body.email, name=body.name)
    except ValueError as e:
        # Keep it simple for MVP.
        from fastapi import HTTPException

        raise HTTPException(status_code=400, detail=str(e)) from e

    access_token = issue_access_token(
        user_id=user["id"],
        email=user["email"],
        name=user.get("name"),
    )

    return AuthResponse(
        access_token=access_token,
        user=UserPublic(
            id=user["id"],
            email=user["email"],
            name=user.get("name"),
            picture=user.get("picture"),
        ),
    )


@router.post("/auth/register", response_model=AuthResponse)
async def auth_register(body: EmailPasswordRegisterRequest) -> AuthResponse:
    first = (body.first_name or "").strip()
    last = (body.last_name or "").strip()
    email = (body.email or "").strip().lower()
    password = body.password

    if not first or not last:
        raise HTTPException(status_code=400, detail="Name is required")
    if not email:
        raise HTTPException(status_code=400, detail="Email is required")

    try:
        user = upsert_user_from_email(email=email, name=f"{first} {last}".strip())
        register_email_password(email=email, password=password, user_id=user["id"])
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    access_token = issue_access_token(
        user_id=user["id"],
        email=user["email"],
        name=user.get("name"),
    )

    return AuthResponse(
        access_token=access_token,
        user=UserPublic(
            id=user["id"],
            email=user["email"],
            name=user.get("name"),
            picture=user.get("picture"),
        ),
    )


@router.post("/auth/login", response_model=AuthResponse)
async def auth_login(body: EmailPasswordLoginRequest) -> AuthResponse:
    user_id = verify_email_password(email=body.email, password=body.password)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    user = get_user(user_id)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    access_token = issue_access_token(
        user_id=user["id"],
        email=user["email"],
        name=user.get("name"),
    )

    return AuthResponse(
        access_token=access_token,
        user=UserPublic(
            id=user["id"],
            email=user["email"],
            name=user.get("name"),
            picture=user.get("picture"),
        ),
    )


@router.get("/me", response_model=UserPublic)
def me(request: Request) -> UserPublic:
    return require_user(request)
