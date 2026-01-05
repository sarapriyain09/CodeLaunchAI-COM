from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

import httpx
import jwt
from fastapi import HTTPException, Request

from app.schemas.auth import UserPublic
from app.services.user_store import get_user


GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "").strip()
JWT_SECRET = (
    os.getenv("JWT_SECRET", "").strip()
    or os.getenv("SECRET_KEY", "").strip()
    or "dev-insecure-change-me"
)
JWT_TTL_MINUTES = int(os.getenv("JWT_TTL_MINUTES", "43200"))  # 30 days


async def verify_google_id_token(id_token: str) -> dict:
    # Verify using Google's tokeninfo endpoint.
    # Production note: local verification is possible, but tokeninfo is simplest for MVP.
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(
            "https://oauth2.googleapis.com/tokeninfo",
            params={"id_token": id_token},
        )

    if resp.status_code != 200:
        raise HTTPException(status_code=401, detail="Invalid Google credential")

    data = resp.json()

    if GOOGLE_CLIENT_ID:
        aud = (data.get("aud") or "").strip()
        if aud != GOOGLE_CLIENT_ID:
            raise HTTPException(status_code=401, detail="Google token audience mismatch")

    email = (data.get("email") or "").strip()
    sub = (data.get("sub") or "").strip()
    email_verified = (str(data.get("email_verified") or "").lower() in {"true", "1", "yes"})

    if not sub or not email:
        raise HTTPException(status_code=401, detail="Google token missing fields")

    if not email_verified:
        raise HTTPException(status_code=401, detail="Google email not verified")

    return data


def issue_access_token(user_id: str, email: str, name: str | None) -> str:
    now = datetime.now(timezone.utc)
    exp = now + timedelta(minutes=JWT_TTL_MINUTES)
    payload = {
        "sub": user_id,
        "email": email,
        "name": name,
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


def _get_bearer_token(request: Request) -> str | None:
    auth = request.headers.get("authorization") or ""
    if not auth.lower().startswith("bearer "):
        return None
    token = auth.split(" ", 1)[1].strip()
    return token or None


def require_user(request: Request) -> UserPublic:
    token = _get_bearer_token(request)
    if not token:
        raise HTTPException(status_code=401, detail="Login required")

    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")

    user_id = str(payload.get("sub") or "")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = get_user(user_id)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return UserPublic(
        id=user.get("id", user_id),
        email=user.get("email", ""),
        name=user.get("name"),
        picture=user.get("picture"),
    )


def try_get_user(request: Request) -> UserPublic | None:
    """Best-effort auth helper.

    Returns None if the request is unauthenticated/invalid, instead of raising 401.
    Useful for trial usage caps and anonymous usage metering.
    """

    token = _get_bearer_token(request)
    if not token:
        return None

    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
    except Exception:
        return None

    user_id = str(payload.get("sub") or "")
    if not user_id:
        return None

    user = get_user(user_id)
    if not user:
        return None

    return UserPublic(
        id=user.get("id", user_id),
        email=user.get("email", ""),
        name=user.get("name"),
        picture=user.get("picture"),
    )

