from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from fastapi import HTTPException

from app.config import WORKSPACES_DIR


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _period_key_utc() -> str:
    now = datetime.now(timezone.utc)
    return f"{now.year:04d}-{now.month:02d}"


def _db_path() -> Path:
    WORKSPACES_DIR.mkdir(parents=True, exist_ok=True)
    return (WORKSPACES_DIR / "_usage.json").resolve()


def _load() -> dict:
    path = _db_path()
    if not path.exists():
        return {"periods": {}}

    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        return {"periods": {}}
    periods = data.get("periods")
    if not isinstance(periods, dict):
        return {"periods": {}}
    return {"periods": periods}


def _atomic_write(path: Path, payload: dict) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    tmp.replace(path)


def usage_limits_enabled() -> bool:
    return os.getenv("USAGE_LIMITS_ENABLED", "true").strip().lower() in {"1", "true", "yes"}


def monthly_credit_limit(*, plan_tier: str) -> int:
    tier = (plan_tier or "student").strip().lower()
    if tier in {"trial", "free"}:
        raw = os.getenv("TRIAL_MONTHLY_CREDITS", "50")
    elif tier in {"trial_expired", "expired"}:
        raw = os.getenv("TRIAL_EXPIRED_MONTHLY_CREDITS", "0")
    elif tier == "enterprise":
        raw = os.getenv("ENTERPRISE_MONTHLY_CREDITS", "0")
    elif tier == "pro":
        raw = os.getenv("PRO_MONTHLY_CREDITS", "300")
    else:
        raw = os.getenv("STUDENT_MONTHLY_CREDITS", "50")
    try:
        limit = int(str(raw).strip())
    except Exception:
        limit = 0
    return max(0, limit)


def credit_cost_for_action(action: str | None) -> int:
    # One credit ≈ one meaningful AI action.
    a = (action or "").strip().lower()
    if not a:
        return 0

    # Defaults are intentionally simple and match the product description:
    # - /plan, /generate, /patch each cost 1
    # - /chat costs 0 (clarification-friendly)
    if a == "chat":
        raw = os.getenv("CREDITS_COST_CHAT", "0")
    elif a == "plan":
        raw = os.getenv("CREDITS_COST_PLAN", "1")
    elif a == "generate":
        raw = os.getenv("CREDITS_COST_GENERATE", "1")
    elif a == "patch":
        raw = os.getenv("CREDITS_COST_PATCH", "1")
    else:
        raw = os.getenv("CREDITS_COST_DEFAULT", "0")

    try:
        return max(0, int(str(raw).strip()))
    except Exception:
        return 0


@dataclass(frozen=True)
class UsageStatus:
    actor: str
    period: str
    credits_used: int
    credits_limit: int
    tokens_used: int

    @property
    def remaining(self) -> int:
        # 0/negative means unlimited.
        if self.credits_limit <= 0:
            return 0
        return max(0, self.credits_limit - self.credits_used)


def get_usage_status(*, actor: str, plan_tier: str) -> UsageStatus:
    period = _period_key_utc()
    data = _load()
    periods = data.get("periods", {})
    period_obj = periods.get(period)
    if not isinstance(period_obj, dict):
        period_obj = {}
    actors = period_obj.get("actors")
    if not isinstance(actors, dict):
        actors = {}
    raw = actors.get(actor)
    if not isinstance(raw, dict):
        raw = {}

    credits_used = raw.get("credits")
    if not isinstance(credits_used, int):
        credits_used = 0
    credits_used = max(0, credits_used)

    tokens_used = raw.get("tokens")
    if not isinstance(tokens_used, int):
        tokens_used = 0
    tokens_used = max(0, tokens_used)

    credits_limit = monthly_credit_limit(plan_tier=plan_tier)
    return UsageStatus(
        actor=actor,
        period=period,
        credits_used=credits_used,
        credits_limit=credits_limit,
        tokens_used=tokens_used,
    )


def ensure_under_limit(*, actor: str, plan_tier: str, credits_to_spend: int) -> UsageStatus:
    if not usage_limits_enabled():
        return get_usage_status(actor=actor, plan_tier=plan_tier)

    status = get_usage_status(actor=actor, plan_tier=plan_tier)
    if credits_to_spend <= 0:
        return status

    # credits_limit <= 0 means unlimited (Enterprise/custom).
    if status.credits_limit > 0 and (status.credits_used + credits_to_spend) > status.credits_limit:
        raise HTTPException(
            status_code=402,
            detail="Monthly AI credits limit reached. Please upgrade your plan or wait for next month.",
        )
    return status


def add_credits(*, actor: str, credits: int) -> UsageStatus:
    credits = int(credits or 0)
    if credits <= 0:
        return get_usage_status(actor=actor, plan_tier="student")

    period = _period_key_utc()
    path = _db_path()
    data = _load()
    periods = data.setdefault("periods", {})
    period_obj = periods.get(period)
    if not isinstance(period_obj, dict):
        period_obj = {}
        periods[period] = period_obj
    actors = period_obj.get("actors")
    if not isinstance(actors, dict):
        actors = {}
        period_obj["actors"] = actors

    entry = actors.get(actor)
    if not isinstance(entry, dict):
        entry = {"tokens": 0, "credits": 0, "requests": 0, "updated_at": _utcnow_iso()}
        actors[actor] = entry

    entry["credits"] = int(entry.get("credits") or 0) + credits
    entry["requests"] = int(entry.get("requests") or 0) + 1
    entry["updated_at"] = _utcnow_iso()

    _atomic_write(path, data)

    # Return status (limit depends on plan; callers can recompute).
    return UsageStatus(
        actor=actor,
        period=period,
        credits_used=int(entry.get("credits") or 0),
        credits_limit=0,
        tokens_used=int(entry.get("tokens") or 0),
    )


def add_tokens(*, actor: str, tokens: int) -> UsageStatus:
    tokens = int(tokens or 0)
    if tokens <= 0:
        return get_usage_status(actor=actor, plan_tier="student")

    period = _period_key_utc()
    path = _db_path()
    data = _load()
    periods = data.setdefault("periods", {})
    period_obj = periods.get(period)
    if not isinstance(period_obj, dict):
        period_obj = {}
        periods[period] = period_obj
    actors = period_obj.get("actors")
    if not isinstance(actors, dict):
        actors = {}
        period_obj["actors"] = actors

    entry = actors.get(actor)
    if not isinstance(entry, dict):
        entry = {"tokens": 0, "credits": 0, "requests": 0, "updated_at": _utcnow_iso()}
        actors[actor] = entry

    entry["tokens"] = int(entry.get("tokens") or 0) + tokens
    entry["updated_at"] = _utcnow_iso()
    _atomic_write(path, data)

    return UsageStatus(
        actor=actor,
        period=period,
        credits_used=int(entry.get("credits") or 0),
        credits_limit=0,
        tokens_used=int(entry.get("tokens") or 0),
    )


def estimate_tokens_from_text(text: str) -> int:
    # Very rough heuristic for non-OpenAI backends.
    # Typical token ~ 3-4 chars in English.
    if not isinstance(text, str) or not text:
        return 0
    return max(1, len(text) // 4)
