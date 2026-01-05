from __future__ import annotations

from contextvars import ContextVar


# Request-scoped identifier used for usage metering.
# Examples:
# - "user:u_abc123" (authenticated)
# - "anon:127.0.0.1" (unauthenticated)
current_usage_actor: ContextVar[str | None] = ContextVar("current_usage_actor", default=None)

current_usage_subscribed: ContextVar[bool] = ContextVar("current_usage_subscribed", default=False)

current_usage_plan_tier: ContextVar[str] = ContextVar("current_usage_plan_tier", default="student")

current_usage_action: ContextVar[str | None] = ContextVar("current_usage_action", default=None)

# Guard so we only charge credits once per request, even if the request triggers
# multiple LLM calls (planner retries, per-page generation, etc.).
current_usage_credits_charged: ContextVar[bool] = ContextVar("current_usage_credits_charged", default=False)


def set_current_usage_actor(actor: str | None) -> None:
    current_usage_actor.set(actor)


def set_current_usage_subscribed(subscribed: bool) -> None:
    current_usage_subscribed.set(bool(subscribed))


def set_current_usage_plan_tier(plan_tier: str) -> None:
    current_usage_plan_tier.set((plan_tier or "student").strip().lower() or "student")


def set_current_usage_action(action: str | None) -> None:
    current_usage_action.set((action or "").strip().lower() or None)


def set_current_usage_credits_charged(charged: bool) -> None:
    current_usage_credits_charged.set(bool(charged))


def get_current_usage_actor() -> str | None:
    return current_usage_actor.get()


def get_current_usage_subscribed() -> bool:
    return bool(current_usage_subscribed.get())


def get_current_usage_plan_tier() -> str:
    return (current_usage_plan_tier.get() or "student").strip().lower() or "student"


def get_current_usage_action() -> str | None:
    v = current_usage_action.get()
    return v.strip().lower() if isinstance(v, str) and v.strip() else None


def get_current_usage_credits_charged() -> bool:
    return bool(current_usage_credits_charged.get())
