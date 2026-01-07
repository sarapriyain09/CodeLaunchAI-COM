from __future__ import annotations

from pathlib import Path

import os
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.responses import FileResponse
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

_DOTENV_PATH = Path(__file__).resolve().parents[1] / '.env'
load_dotenv(dotenv_path=_DOTENV_PATH, override=True)

from app.routes.plan import router as plan_router
from app.routes.chat import router as chat_router
from app.routes.auth import router as auth_router
from app.routes.projects import router as projects_router
from app.routes.generate import router as generate_router
from app.routes.preview import router as preview_router
from app.routes.export import router as export_router
from app.routes.billing import router as billing_router
from app.routes.patch import router as patch_router
from app.routes.project_state import router as project_state_router
from app.routes.project_files import router as project_files_router
from app.routes.usage import router as usage_router
from app.db_init import init_db_startup

from app.services.auth import try_get_user
import os

from app.services.subscription import is_subscribed
from app.services.user_store import get_user
from app.services.usage_context import (
    set_current_usage_action,
    set_current_usage_actor,
    set_current_usage_credits_charged,
    set_current_usage_plan_tier,
    set_current_usage_subscribed,
)
from app.services.request_ip import get_request_client_ip
from app.services.rate_limiter import check_rate_limit, rate_limits_enabled
from app.services.anon_identity import COOKIE_NAME as ANON_COOKIE_NAME, get_or_create_anon_id


def _parse_iso8601(s: str | None) -> datetime | None:
    if not isinstance(s, str) or not s.strip():
        return None
    v = s.strip()
    try:
        if v.endswith("Z"):
            v = v[:-1] + "+00:00"
        dt = datetime.fromisoformat(v)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None

app = FastAPI(title='CodeLaunch Orchestrator', version='0.1.0')


@app.middleware("http")
async def _usage_actor_middleware(request: Request, call_next):
    # Prefer authenticated user id; fallback to IP-based anonymous id.
    user = try_get_user(request)
    new_anon_cookie: str | None = None
    if user and user.id:
        actor = f"user:{user.id}"
    else:
        anon_mode = (os.getenv("ANON_ACTOR_MODE", "cookie") or "cookie").strip().lower()
        if anon_mode == "ip":
            host = get_request_client_ip(request)
            actor = f"anon:{host}"
        else:
            anon_id, is_new = get_or_create_anon_id(request)
            actor = f"anon:{anon_id}"
            if is_new:
                new_anon_cookie = anon_id

    set_current_usage_actor(actor)

    subscribed = bool(is_subscribed(user)) if user else False
    set_current_usage_subscribed(subscribed)

    # Tier selection:
    # - Enterprise: allowlist
    # - Paid plans: infer from Stripe webhook metadata (subscription_plan)
    # - Free trial: time-limited window for non-subscribed users
    enterprise = {e.strip().lower() for e in (os.getenv("ENTERPRISE_EMAILS", "").split(",")) if e.strip()}
    plan_tier = "trial"

    raw_user = get_user(user.id) if (user and user.id) else None
    sub_plan = (raw_user.get("subscription_plan") if isinstance(raw_user, dict) else None)
    sub_plan = (sub_plan or "").strip().lower()

    if user and user.email and user.email.strip().lower() in enterprise:
        plan_tier = "enterprise"
    elif subscribed:
        # Paid
        plan_tier = "student" if sub_plan == "student" else "pro"
    else:
        # Free trial logic
        trial_enabled = os.getenv("TRIAL_ENABLED", "true").strip().lower() in {"1", "true", "yes"}
        trial_days_raw = os.getenv("TRIAL_DAYS", "14")
        try:
            trial_days = max(0, int(str(trial_days_raw).strip()))
        except Exception:
            trial_days = 14

        if not trial_enabled:
            plan_tier = "trial_expired"
        elif trial_days <= 0:
            plan_tier = "trial"
        else:
            created_at = _parse_iso8601(raw_user.get("created_at") if isinstance(raw_user, dict) else None)
            if created_at is None:
                # Anonymous or missing created_at -> treat as active trial
                plan_tier = "trial"
            else:
                trial_end = created_at + timedelta(days=trial_days)
                plan_tier = "trial" if datetime.now(timezone.utc) < trial_end else "trial_expired"

    set_current_usage_plan_tier(plan_tier)

    # Map endpoint -> usage action.
    # This is used for credit charging (1 credit per meaningful action).
    action: str | None = None
    path = (request.url.path or "").rstrip("/")
    if request.method.upper() == "POST":
        if path == "/plan":
            action = "plan"
        elif path == "/generate":
            action = "generate"
        elif path.endswith("/patch"):
            action = "patch"
        elif path == "/chat" or path.endswith("/chat"):
            action = "chat"
    set_current_usage_action(action)
    set_current_usage_credits_charged(False)

    # Basic rate limiting (per actor per action) for high-cost endpoints.
    # Keeps abuse in check even when credits are not charged (e.g., chat=0 credits).
    if rate_limits_enabled() and request.method.upper() == "POST" and action in {"plan", "chat", "patch"}:
        rl = check_rate_limit(actor=actor, action=action)
        if not rl.allowed:
            headers = {
                "Retry-After": str(rl.retry_after_seconds),
                "X-RateLimit-Limit": str(rl.limit),
                "X-RateLimit-Remaining": "0",
            }
            return JSONResponse(
                status_code=429,
                headers=headers,
                content={
                    "detail": "Rate limit exceeded",
                    "action": action,
                    "limit_per_minute": rl.limit,
                    "retry_after_seconds": rl.retry_after_seconds,
                },
            )

    response = await call_next(request)

    # If we generated a new anon id, persist it so usage is per-browser, not per-IP.
    if new_anon_cookie:
        # Secure cookies only over https.
        secure = (request.url.scheme or "").lower() == "https"
        response.set_cookie(
            key=ANON_COOKIE_NAME,
            value=new_anon_cookie,
            max_age=60 * 60 * 24 * 365 * 2,
            httponly=True,
            samesite="lax",
            secure=secure,
            path="/",
        )

    return response


@app.on_event('startup')
def _startup() -> None:
    # Creates tables in Postgres when DATABASE_URL is set.
    # Provides clearer logs + optional retry/fail-open.
    init_db_startup()

# Workspace root (…/codelaunchcom). Used to serve public static pages in dev/prod.
_WORKSPACE_ROOT = Path(__file__).resolve().parents[3]

def _parse_cors_origins(raw: str | None) -> list[str]:
    value = (raw or '').strip()
    if not value:
        return ['*']
    return [part.strip() for part in value.split(',') if part.strip()]


cors_origins = _parse_cors_origins(os.getenv('CORS_ALLOW_ORIGINS'))
cors_allow_credentials = (os.getenv('CORS_ALLOW_CREDENTIALS', 'false').strip().lower() == 'true')

# Allow a regex for local dev origins (e.g., different Vite ports) without needing
# to enumerate every port. Enabled automatically when loopback origins are present.
cors_origin_regex = (os.getenv('CORS_ALLOW_ORIGIN_REGEX') or '').strip() or None
if cors_origin_regex is None and cors_origins != ['*']:
    has_loopback = any(
        ('localhost' in origin) or ('127.0.0.1' in origin) or ('[::1]' in origin)
        for origin in cors_origins
        if isinstance(origin, str)
    )
    if has_loopback:
        cors_origin_regex = r'^https?://(localhost|127\.0\.0\.1|\[::1\])(:\d+)?$'

# Browsers will reject Access-Control-Allow-Origin: * when credentials are enabled.
if cors_allow_credentials and cors_origins == ['*']:
    cors_allow_credentials = False

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_origin_regex=cors_origin_regex,
    allow_credentials=cors_allow_credentials,
    allow_methods=['*'],
    allow_headers=['*'],
)


@app.get('/health')
def health_check() -> dict[str, bool]:
    return {'ok': True}


@app.get('/', include_in_schema=False)
def public_home() -> RedirectResponse:
    # If frontend is hosted separately (e.g., www domain) set APP_BASE_URL to send
    # users there when they visit the backend directly.
    app_base_url = (os.getenv('APP_BASE_URL') or '').strip()
    if app_base_url:
        return RedirectResponse(url=app_base_url)
    return RedirectResponse(url='/app/')


@app.get('/subscribe.html', include_in_schema=False)
def public_subscribe() -> FileResponse:
    subscribe_path = _WORKSPACE_ROOT / 'subscribe.html'
    return FileResponse(subscribe_path)


# Serve the built frontend app from the backend.
# Vite build output goes to workspace_root/app (see frontend/vite.config.ts).
_APP_BUILD_DIR = _WORKSPACE_ROOT / 'app'
if _APP_BUILD_DIR.exists():
    app.mount('/app', StaticFiles(directory=str(_APP_BUILD_DIR), html=True), name='app')


@app.get('/app', include_in_schema=False)
def app_root_redirect() -> RedirectResponse:
    return RedirectResponse(url='/app/')


app.include_router(plan_router)
app.include_router(chat_router)
app.include_router(auth_router)
app.include_router(projects_router)
app.include_router(generate_router)
app.include_router(preview_router, tags=["preview"])
app.include_router(export_router)
app.include_router(billing_router)
app.include_router(project_state_router)
app.include_router(project_files_router)
app.include_router(patch_router)
app.include_router(usage_router)

