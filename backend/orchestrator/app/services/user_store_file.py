from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path

from app.config import WORKSPACES_DIR


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
    data = _load()
    for u in data.get("users", []):
        if u.get("id") == user_id:
            return u
    return None


def _update_user(user_id: str, patch: dict) -> dict | None:
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
) -> dict | None:
    patch: dict = {
        "subscription_status": status,
        "subscription_current_period_end": current_period_end,
    }
    return _update_user(user_id, patch)
