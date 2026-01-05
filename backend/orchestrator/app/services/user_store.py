from __future__ import annotations

import os
import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select

from app.config import WORKSPACES_DIR
from app.db import db_enabled, session_scope
from app.db_models import User


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _db_path() -> Path:
    WORKSPACES_DIR.mkdir(parents=True, exist_ok=True)
    return (WORKSPACES_DIR / "_users.json").resolve()


def _load() -> dict:
    path = _db_path()
    if not path.exists():
        return {"users": []}

    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, dict):
        return {"users": []}

    users = data.get("users")
    if not isinstance(users, list):
        return {"users": []}

    return {"users": [u for u in users if isinstance(u, dict)]}


def _atomic_write(path: Path, payload: dict) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    tmp.replace(path)


def upsert_user_from_google(sub: str, email: str, name: str | None, picture: str | None) -> dict:
    if db_enabled():
        email_norm = (email or "").strip().lower()
        now = datetime.now(timezone.utc)
        with session_scope() as session:
            existing = session.execute(select(User).where(User.email == email_norm)).scalar_one_or_none()
            if existing is None:
                user = User(
                    id=f"u_{uuid.uuid4().hex}",
                    email=email_norm,
                    name=name,
                    picture=picture,
                    last_login_at=now,
                )
                session.add(user)
                session.flush()
                return {
                    "id": user.id,
                    "email": user.email,
                    "name": user.name,
                    "picture": user.picture,
                    "created_at": user.created_at.isoformat().replace("+00:00", "Z") if user.created_at else None,
                    "last_login_at": user.last_login_at.isoformat().replace("+00:00", "Z") if user.last_login_at else None,
                    "stripe_customer_id": user.stripe_customer_id,
                    "subscription_status": user.subscription_status,
                    "subscription_current_period_end": user.subscription_current_period_end,
                }

            existing.email = email_norm
            existing.name = name
            existing.picture = picture
            existing.last_login_at = now
            session.flush()
            return {
                "id": existing.id,
                "email": existing.email,
                "name": existing.name,
                "picture": existing.picture,
                "created_at": existing.created_at.isoformat().replace("+00:00", "Z") if existing.created_at else None,
                "last_login_at": existing.last_login_at.isoformat().replace("+00:00", "Z") if existing.last_login_at else None,
                "stripe_customer_id": existing.stripe_customer_id,
                "subscription_status": existing.subscription_status,
                "subscription_current_period_end": existing.subscription_current_period_end,
                    "subscription_plan": getattr(existing, "subscription_plan", None),
                    "subscription_interval": getattr(existing, "subscription_interval", None),
            }

    data = _load()
    users: list[dict] = data.get("users", [])

    now = _utcnow_iso()
    existing = next((u for u in users if u.get("id") == sub), None)

    if existing is None:
        user = {
            "id": sub,
            "email": email,
            "name": name,
            "picture": picture,
            "created_at": now,
            "last_login_at": now,
            # Billing/subscription (optional; set via Stripe webhook)
            "stripe_customer_id": None,
            "subscription_status": None,
            "subscription_current_period_end": None,
            "subscription_plan": None,
            "subscription_interval": None,
        }
        users.append(user)
    else:
        existing["email"] = email
        existing["name"] = name
        existing["picture"] = picture
        existing["last_login_at"] = now
        # Keep existing billing fields if present; don't overwrite here.
        user = existing

    _atomic_write(_db_path(), {"users": users})
    return user


_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def upsert_user_from_email(*, email: str, name: str | None) -> dict:
    if db_enabled():
        email_norm = (email or "").strip().lower()
        if not email_norm or len(email_norm) < 5 or not _EMAIL_RE.match(email_norm):
            raise ValueError("Invalid email")

        now = datetime.now(timezone.utc)
        with session_scope() as session:
            existing = session.execute(select(User).where(User.email == email_norm)).scalar_one_or_none()
            if existing is None:
                user = User(
                    id=f"u_{uuid.uuid4().hex}",
                    email=email_norm,
                    name=(name or None),
                    picture=None,
                    last_login_at=now,
                )
                session.add(user)
                session.flush()
                return {
                    "id": user.id,
                    "email": user.email,
                    "name": user.name,
                    "picture": user.picture,
                    "created_at": user.created_at.isoformat().replace("+00:00", "Z") if user.created_at else None,
                    "last_login_at": user.last_login_at.isoformat().replace("+00:00", "Z") if user.last_login_at else None,
                    "stripe_customer_id": user.stripe_customer_id,
                    "subscription_status": user.subscription_status,
                    "subscription_current_period_end": user.subscription_current_period_end,
                }

            existing.name = (name or existing.name)
            existing.last_login_at = now
            session.flush()
            return {
                "id": existing.id,
                "email": existing.email,
                "name": existing.name,
                "picture": existing.picture,
                "created_at": existing.created_at.isoformat().replace("+00:00", "Z") if existing.created_at else None,
                "last_login_at": existing.last_login_at.isoformat().replace("+00:00", "Z") if existing.last_login_at else None,
                "stripe_customer_id": existing.stripe_customer_id,
                "subscription_status": existing.subscription_status,
                "subscription_current_period_end": existing.subscription_current_period_end,
                    "subscription_plan": getattr(existing, "subscription_plan", None),
                    "subscription_interval": getattr(existing, "subscription_interval", None),
            }

    email_norm = (email or "").strip().lower()
    if not email_norm or len(email_norm) < 5 or not _EMAIL_RE.match(email_norm):
        raise ValueError("Invalid email")

    data = _load()
    users: list[dict] = data.get("users", [])

    now = _utcnow_iso()
    existing = next((u for u in users if str(u.get("email") or "").strip().lower() == email_norm), None)
    if existing is None:
        user_id = f"u_{uuid.uuid4().hex}"
        user = {
            "id": user_id,
            "email": email_norm,
            "name": (name or None),
            "picture": None,
            "created_at": now,
            "last_login_at": now,
            "stripe_customer_id": None,
            "subscription_status": None,
            "subscription_current_period_end": None,
            "subscription_plan": None,
            "subscription_interval": None,
        }
        users.append(user)
    else:
        existing["email"] = email_norm
        existing["name"] = (name or existing.get("name"))
        existing["last_login_at"] = now
        user = existing

    _atomic_write(_db_path(), {"users": users})
    return user


def get_user(user_id: str) -> dict | None:
    if db_enabled():
        with session_scope() as session:
            row = session.get(User, user_id)
            if row is None:
                return None
            return {
                "id": row.id,
                "email": row.email,
                "name": row.name,
                "picture": row.picture,
                "created_at": row.created_at.isoformat().replace("+00:00", "Z") if row.created_at else None,
                "last_login_at": row.last_login_at.isoformat().replace("+00:00", "Z") if row.last_login_at else None,
                "stripe_customer_id": row.stripe_customer_id,
                "subscription_status": row.subscription_status,
                "subscription_current_period_end": row.subscription_current_period_end,
                    "subscription_plan": getattr(row, "subscription_plan", None),
                    "subscription_interval": getattr(row, "subscription_interval", None),
            }

    data = _load()
    for u in data.get("users", []):
        if u.get("id") == user_id:
            return u
    return None


def _update_user(user_id: str, patch: dict) -> dict | None:
    if db_enabled():
        with session_scope() as session:
            row = session.get(User, user_id)
            if row is None:
                return None
            for k, v in patch.items():
                if hasattr(row, k):
                    setattr(row, k, v)
            session.flush()
            return {
                "id": row.id,
                "email": row.email,
                "name": row.name,
                "picture": row.picture,
                "created_at": row.created_at.isoformat().replace("+00:00", "Z") if row.created_at else None,
                "last_login_at": row.last_login_at.isoformat().replace("+00:00", "Z") if row.last_login_at else None,
                "stripe_customer_id": row.stripe_customer_id,
                "subscription_status": row.subscription_status,
                "subscription_current_period_end": row.subscription_current_period_end,
                    "subscription_plan": getattr(row, "subscription_plan", None),
                    "subscription_interval": getattr(row, "subscription_interval", None),
            }

    data = _load()
    users: list[dict] = data.get("users", [])
    user = next((u for u in users if u.get("id") == user_id), None)
    if user is None:
        return None
    user.update(patch)
    _atomic_write(_db_path(), {"users": users})
    return user


def find_user_by_stripe_customer_id(customer_id: str) -> dict | None:
    if not customer_id:
        return None

    if db_enabled():
        with session_scope() as session:
            row = session.execute(select(User).where(User.stripe_customer_id == customer_id)).scalar_one_or_none()
            if row is None:
                return None
            return {
                "id": row.id,
                "email": row.email,
                "name": row.name,
                "picture": row.picture,
                "created_at": row.created_at.isoformat().replace("+00:00", "Z") if row.created_at else None,
                "last_login_at": row.last_login_at.isoformat().replace("+00:00", "Z") if row.last_login_at else None,
                "stripe_customer_id": row.stripe_customer_id,
                "subscription_status": row.subscription_status,
                "subscription_current_period_end": row.subscription_current_period_end,
                    "subscription_plan": getattr(row, "subscription_plan", None),
                    "subscription_interval": getattr(row, "subscription_interval", None),
            }

    data = _load()
    for u in data.get("users", []):
        if u.get("stripe_customer_id") == customer_id:
            return u
    return None


def set_stripe_customer_id(user_id: str, customer_id: str) -> dict | None:
    if not customer_id:
        return get_user(user_id)
    return _update_user(user_id, {"stripe_customer_id": customer_id})


def set_subscription_status(
    *,
    user_id: str,
    status: str | None,
    current_period_end: int | None,
    plan: str | None = None,
    interval: str | None = None,
) -> dict | None:
    patch: dict = {
        "subscription_status": status,
        "subscription_current_period_end": current_period_end,
        "subscription_plan": plan,
        "subscription_interval": interval,
    }
    return _update_user(user_id, patch)
