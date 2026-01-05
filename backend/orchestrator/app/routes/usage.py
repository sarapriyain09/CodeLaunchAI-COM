from __future__ import annotations

from fastapi import APIRouter, Request

from app.services.auth import try_get_user
from app.services.subscription import is_subscribed
from app.services.usage_context import get_current_usage_actor, get_current_usage_plan_tier
from app.services.usage_store import get_usage_status
import os


router = APIRouter()


def _parse_allowlist(raw: str) -> set[str]:
    return {e.strip().lower() for e in (raw or "").split(",") if e.strip()}


def _trial_days() -> int:
    raw = os.getenv("TRIAL_DAYS", "14")
    try:
        return max(0, int(str(raw).strip()))
    except Exception:
        return 14


@router.get("/usage/status")
def usage_status(request: Request) -> dict:
    plan_tier = get_current_usage_plan_tier()
    subscribed = (plan_tier in {"student", "pro", "enterprise"})

    actor = get_current_usage_actor()
    if not actor:
        host = (request.client.host if request.client else "unknown")
        actor = f"anon:{host}"

    status = get_usage_status(actor=actor, plan_tier=plan_tier)
    trial_active = (plan_tier == "trial")
    return {
        "period": status.period,
        "plan_tier": plan_tier,
        "credits_used": status.credits_used,
        "credits_limit": status.credits_limit,
        "credits_remaining": status.remaining,
        "tokens_used": status.tokens_used,
        "subscribed": bool(subscribed),
        "trial_active": bool(trial_active),
        "trial_days": _trial_days(),
        "actor": actor,
    }
