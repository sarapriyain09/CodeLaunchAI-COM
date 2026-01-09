from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
from datetime import datetime, timezone
from pathlib import Path

from app.config import WORKSPACES_DIR


_PBKDF2_ITERS = 200_000


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _db_path() -> Path:
    WORKSPACES_DIR.mkdir(parents=True, exist_ok=True)
    return (WORKSPACES_DIR / "_credentials.json").resolve()


def _load() -> dict:
    path = _db_path()
    if not path.exists():
        return {"credentials": []}

    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, dict):
        return {"credentials": []}

    rows = data.get("credentials")
    if not isinstance(rows, list):
        return {"credentials": []}

    cleaned: list[dict] = [r for r in rows if isinstance(r, dict)]
    return {"credentials": cleaned}


def _atomic_write(path: Path, payload: dict) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    tmp.replace(path)


def _norm_email(email: str) -> str:
    return (email or "").strip().lower()


def _hash_password(password: str, salt: bytes) -> bytes:
    pw = (password or "").encode("utf-8")
    return hashlib.pbkdf2_hmac("sha256", pw, salt, _PBKDF2_ITERS)


def register_email_password(*, email: str, password: str, user_id: str) -> None:
    """Register a new email/password credential.

    Stores credential material in a JSON file under WORKSPACES_DIR so it works
    even when the main user profile is stored in Postgres.
    """

    email_norm = _norm_email(email)
    if not email_norm:
        raise ValueError("Email is required")
    if not password or len(password) < 8:
        raise ValueError("Password must be at least 8 characters")
    if not user_id:
        raise ValueError("Invalid user")

    data = _load()
    rows: list[dict] = data.get("credentials", [])

    existing = next((r for r in rows if _norm_email(str(r.get("email") or "")) == email_norm), None)
    if existing is not None:
        raise ValueError("Account already exists. Please log in.")

    salt = secrets.token_bytes(16)
    digest = _hash_password(password, salt)

    now = _utcnow_iso()
    rows.append(
        {
            "email": email_norm,
            "user_id": user_id,
            "salt": base64.b64encode(salt).decode("ascii"),
            "hash": base64.b64encode(digest).decode("ascii"),
            "created_at": now,
            "updated_at": now,
        }
    )

    _atomic_write(_db_path(), {"credentials": rows})


def verify_email_password(*, email: str, password: str) -> str | None:
    """Return user_id if the password matches, else None."""

    email_norm = _norm_email(email)
    if not email_norm or not password:
        return None

    data = _load()
    rows: list[dict] = data.get("credentials", [])
    existing = next((r for r in rows if _norm_email(str(r.get("email") or "")) == email_norm), None)
    if not existing:
        return None

    try:
        salt = base64.b64decode(str(existing.get("salt") or ""))
        expected = base64.b64decode(str(existing.get("hash") or ""))
    except Exception:
        return None

    computed = _hash_password(password, salt)
    if not hmac.compare_digest(computed, expected):
        return None

    user_id = str(existing.get("user_id") or "").strip()
    return user_id or None
