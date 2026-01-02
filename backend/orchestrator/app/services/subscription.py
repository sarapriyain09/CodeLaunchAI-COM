from __future__ import annotations

import os

from app.schemas.auth import UserPublic
from app.services.user_store import get_user


def _parse_allowlist(raw: str) -> set[str]:
    return {e.strip().lower() for e in raw.split(",") if e.strip()}


def is_subscription_required() -> bool:
    return (os.getenv("SUBSCRIPTION_REQUIRED", "true").strip().lower() in {"1", "true", "yes"})


def is_subscribed(user: UserPublic) -> bool:
    # MVP gate: email allowlist.
    if not is_subscription_required():
        return True

    allow = _parse_allowlist(os.getenv("SUBSCRIBER_EMAILS", ""))
    if not allow:
        allow = set()

    if user.email.strip().lower() in allow:
        return True

    # Stripe-backed subscription (set by webhook)
    raw = get_user(user.id) or {}
    status = (raw.get("subscription_status") or "").strip().lower()
    return status in {"active", "trialing"}
