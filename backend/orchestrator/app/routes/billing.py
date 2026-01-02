from __future__ import annotations

import os

import stripe
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.schemas.auth import UserPublic
from app.services.auth import require_user
from app.services.subscription import is_subscribed
from app.services.user_store import (
    find_user_by_stripe_customer_id,
    set_stripe_customer_id,
    set_subscription_status,
)

router = APIRouter()

STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "").strip()
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "").strip()

# App-generator tiers.
STRIPE_PRICE_STUDENT = os.getenv("STRIPE_PRICE_STUDENT", "").strip()
STRIPE_PRICE_PRO = os.getenv("STRIPE_PRICE_PRO", "").strip()

# App-generator tiers with interval split.
STRIPE_PRICE_STUDENT_MONTHLY = os.getenv("STRIPE_PRICE_STUDENT_MONTHLY", "").strip()
STRIPE_PRICE_STUDENT_YEARLY = os.getenv("STRIPE_PRICE_STUDENT_YEARLY", "").strip()
STRIPE_PRICE_PRO_MONTHLY = os.getenv("STRIPE_PRICE_PRO_MONTHLY", "").strip()
STRIPE_PRICE_PRO_YEARLY = os.getenv("STRIPE_PRICE_PRO_YEARLY", "").strip()

# Optional: separate price ids for monthly/yearly (if you ever switch to interval-based pricing).
STRIPE_PRICE_ID_MONTHLY = os.getenv("STRIPE_PRICE_ID_MONTHLY", "").strip()
STRIPE_PRICE_ID_YEARLY = os.getenv("STRIPE_PRICE_ID_YEARLY", "").strip()

# Back-compat: a single price id used for all subscriptions.
STRIPE_PRICE_ID = os.getenv("STRIPE_PRICE_ID", "").strip()

# Where Stripe should send users back after checkout.
# Example: https://yourdomain.com/app/  (HashRouter will handle #/builder)
APP_BASE_URL = os.getenv("APP_BASE_URL", "http://localhost:8080/app/").strip()

# Optional: override success/cancel URLs (useful for standalone HTML billing pages).
BILLING_SUCCESS_URL = os.getenv("BILLING_SUCCESS_URL", "").strip()
BILLING_CANCEL_URL = os.getenv("BILLING_CANCEL_URL", "").strip()

if STRIPE_SECRET_KEY:
    stripe.api_key = STRIPE_SECRET_KEY


class CheckoutSessionRequest(BaseModel):
    plan: str = "pro"
    interval: str = "month"


def _normalize_plan(value: str) -> str:
    plan = (value or "").strip().lower()
    if plan in {"student", "pro"}:
        return plan
    raise HTTPException(status_code=400, detail="Invalid plan. Use: student or pro")


def _normalize_interval(value: str) -> str:
    interval = (value or "").strip().lower()
    if interval in {"month", "monthly"}:
        return "month"
    if interval in {"year", "yearly", "annual", "annually"}:
        return "year"
    raise HTTPException(status_code=400, detail="Invalid interval. Use: month or year")


def _stripe_price_id_for(plan: str, interval: str) -> str:
    plan_norm = _normalize_plan(plan)
    interval_norm = _normalize_interval(interval)

    # Tiered pricing (Student/Pro) with monthly/yearly.
    if plan_norm == "student":
        candidate = STRIPE_PRICE_STUDENT_YEARLY if interval_norm == "year" else STRIPE_PRICE_STUDENT_MONTHLY
        if candidate:
            if not candidate.startswith("price_"):
                raise HTTPException(
                    status_code=500,
                    detail=f"Invalid {'STRIPE_PRICE_STUDENT_YEARLY' if interval_norm == 'year' else 'STRIPE_PRICE_STUDENT_MONTHLY'} (must start with price_)",
                )
            return candidate
        # Fallback: single Student price id (no interval split)
        if STRIPE_PRICE_STUDENT:
            if not STRIPE_PRICE_STUDENT.startswith("price_"):
                raise HTTPException(status_code=500, detail="Invalid STRIPE_PRICE_STUDENT (must start with price_)")
            return STRIPE_PRICE_STUDENT

    if plan_norm == "pro":
        candidate = STRIPE_PRICE_PRO_YEARLY if interval_norm == "year" else STRIPE_PRICE_PRO_MONTHLY
        if candidate:
            if not candidate.startswith("price_"):
                raise HTTPException(
                    status_code=500,
                    detail=f"Invalid {'STRIPE_PRICE_PRO_YEARLY' if interval_norm == 'year' else 'STRIPE_PRICE_PRO_MONTHLY'} (must start with price_)",
                )
            return candidate
        # Fallback: single Pro price id (no interval split)
        if STRIPE_PRICE_PRO:
            if not STRIPE_PRICE_PRO.startswith("price_"):
                raise HTTPException(status_code=500, detail="Invalid STRIPE_PRICE_PRO (must start with price_)")
            return STRIPE_PRICE_PRO

    # App-generator MVP: one subscription, choose monthly vs yearly.
    if interval_norm == "month" and STRIPE_PRICE_ID_MONTHLY:
        if not STRIPE_PRICE_ID_MONTHLY.startswith("price_"):
            raise HTTPException(status_code=500, detail="Invalid STRIPE_PRICE_ID_MONTHLY (must start with price_)")
        return STRIPE_PRICE_ID_MONTHLY
    if interval_norm == "year" and STRIPE_PRICE_ID_YEARLY:
        if not STRIPE_PRICE_ID_YEARLY.startswith("price_"):
            raise HTTPException(status_code=500, detail="Invalid STRIPE_PRICE_ID_YEARLY (must start with price_)")
        return STRIPE_PRICE_ID_YEARLY

    # Back-compat: single price id.
    if STRIPE_PRICE_ID:
        if not STRIPE_PRICE_ID.startswith("price_"):
            raise HTTPException(
                status_code=500,
                detail="STRIPE_PRICE_ID looks wrong. Use a Stripe Price ID that starts with price_ (not prod_).",
            )
        return STRIPE_PRICE_ID

    raise HTTPException(
        status_code=500,
        detail=(
            "Stripe pricing not configured. Set STRIPE_PRICE_STUDENT_MONTHLY/YEARLY and STRIPE_PRICE_PRO_MONTHLY/YEARLY "
            "(preferred), or set STRIPE_PRICE_ID for a single plan."
        ),
    )


def _require_stripe_config() -> None:
    if not STRIPE_SECRET_KEY:
        raise HTTPException(status_code=500, detail="Stripe is not configured (missing STRIPE_SECRET_KEY)")


@router.get("/billing/status")
def billing_status(request: Request) -> dict:
    user: UserPublic = require_user(request)
    return {
        "subscribed": bool(is_subscribed(user)),
    }


@router.post("/billing/checkout-session")
def create_checkout_session(request: Request, payload: CheckoutSessionRequest | None = None) -> dict:
    user: UserPublic = require_user(request)
    _require_stripe_config()

    # If already subscribed, no need to send them to Stripe.
    if is_subscribed(user):
        return {"already_subscribed": True, "url": None}

    effective = payload or CheckoutSessionRequest()
    price_id = _stripe_price_id_for(effective.plan, effective.interval)

    try:
        success_url = BILLING_SUCCESS_URL or f"{APP_BASE_URL}#/builder?subscribed=1"
        cancel_url = BILLING_CANCEL_URL or f"{APP_BASE_URL}#/builder?canceled=1"
        session = stripe.checkout.Session.create(
            mode="subscription",
            client_reference_id=user.id,
            customer_email=user.email,
            line_items=[{"price": price_id, "quantity": 1}],
            success_url=success_url,
            cancel_url=cancel_url,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to create checkout session: {e}") from e

    return {"url": session.url}


@router.post("/billing/webhook")
async def stripe_webhook(request: Request):
    if not STRIPE_WEBHOOK_SECRET:
        raise HTTPException(status_code=500, detail="Stripe webhook not configured")

    payload = await request.body()
    sig = request.headers.get("stripe-signature") or ""

    try:
        event = stripe.Webhook.construct_event(payload=payload, sig_header=sig, secret=STRIPE_WEBHOOK_SECRET)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid webhook signature: {e}") from e

    etype = event.get("type")
    data_obj = (event.get("data") or {}).get("object") or {}

    # 1) Checkout completed: capture Stripe customer id and map to our user.
    if etype == "checkout.session.completed":
        user_id = (data_obj.get("client_reference_id") or "").strip()
        customer_id = (data_obj.get("customer") or "").strip()
        if user_id and customer_id:
            set_stripe_customer_id(user_id, customer_id)

    # 2) Subscription lifecycle: update user subscription status.
    if etype in {"customer.subscription.created", "customer.subscription.updated", "customer.subscription.deleted"}:
        customer_id = (data_obj.get("customer") or "").strip()
        status = data_obj.get("status")
        current_period_end = data_obj.get("current_period_end")

        user = find_user_by_stripe_customer_id(customer_id)
        if user and user.get("id"):
            set_subscription_status(
                user_id=str(user["id"]),
                status=str(status) if status is not None else None,
                current_period_end=int(current_period_end) if isinstance(current_period_end, int) else None,
            )

    return {"ok": True}
