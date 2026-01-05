from __future__ import annotations

import logging
import os
import time

from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from app.db import db_disabled_reason, db_enabled, describe_database_url, disable_db, get_engine
from app.db_models import Base


logger = logging.getLogger(__name__)


def _truthy_env(name: str, default: str = "false") -> bool:
    return (os.getenv(name, default).strip().lower() in {"1", "true", "yes", "on"})


def _db_failure_hints(exc: Exception) -> list[str]:
    msg = str(exc).lower()
    hints: list[str] = []

    # DNS / bad hostname: common when a Render hostname is copied incompletely.
    if (
        "name or service not known" in msg
        or "temporary failure in name resolution" in msg
        or "getaddrinfo failed" in msg
        or "no such host" in msg
        or "nodename nor servname provided" in msg
    ):
        hints.append("DB host DNS lookup failed. Double-check DATABASE_URL host; on Render use the exact value from the Render dashboard.")

    # SSL / cert / handshake issues.
    if "ssl" in msg and "mode" in msg:
        hints.append("If your provider requires TLS, add ?sslmode=require (or the provider-recommended sslmode) to DATABASE_URL.")

    if "password authentication failed" in msg:
        hints.append("DB credentials rejected. Verify username/password in DATABASE_URL.")

    if "connection refused" in msg or "could not connect" in msg:
        hints.append("DB is unreachable. Verify host/port and that the DB is running/accessible from this service.")

    return hints


def init_db() -> None:
    if not db_enabled():
        return

    engine = get_engine()
    Base.metadata.create_all(bind=engine)

    # Minimal migration support (dev-friendly): add new columns if missing.
    # This avoids requiring Alembic for the MVP.
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                ALTER TABLE projects
                ADD COLUMN IF NOT EXISTS generated_files JSONB NOT NULL DEFAULT '[]'::jsonb;
                """
            )
        )


def init_db_startup() -> None:
    """Initialize DB during app startup with clearer failures.

    Behavior is controlled by env vars:
    - DB_INIT_ON_STARTUP (default: true)
    - DB_STARTUP_RETRY_ATTEMPTS (default: 0)
    - DB_STARTUP_RETRY_DELAY_SECONDS (default: 1.0)
    - DB_FAIL_OPEN (default: false) -> disables DB usage and continues startup
    """

    if not _truthy_env("DB_INIT_ON_STARTUP", "true"):
        return

    if not db_enabled():
        return

    attempts = int(os.getenv("DB_STARTUP_RETRY_ATTEMPTS", "0") or "0")
    delay_s = float(os.getenv("DB_STARTUP_RETRY_DELAY_SECONDS", "1.0") or "1.0")
    delay_s = max(0.0, delay_s)
    fail_open = _truthy_env("DB_FAIL_OPEN", "false")

    last_exc: Exception | None = None
    for attempt in range(attempts + 1):
        try:
            init_db()
            if db_disabled_reason():
                # In case something disabled the DB earlier.
                logger.warning("DB init succeeded but DB is currently disabled: %s", db_disabled_reason())
            logger.info("DB init OK (%s)", describe_database_url())
            return
        except OperationalError as exc:
            last_exc = exc
            hints = _db_failure_hints(exc)
            hint_text = (" " + " ".join(f"Hint: {h}" for h in hints)) if hints else ""

            # Include a short, safe error detail (no secrets).
            detail_obj = getattr(exc, "orig", None) or exc
            detail = str(detail_obj).strip().replace("\n", " ")
            if len(detail) > 220:
                detail = detail[:220] + "..."

            if attempt < attempts:
                logger.warning(
                    "DB connection failed during startup (attempt %s/%s). %s.%s Retrying in %.1fs...",
                    attempt + 1,
                    attempts + 1,
                    describe_database_url(),
                    hint_text,
                    delay_s,
                )
                time.sleep(delay_s)
                continue

            # Final attempt failed.
            message = (
                f"DB connection failed during startup. {describe_database_url()}. "
                f"Error: {detail}."
                f"{hint_text} "
                "To start without Postgres (local/dev), set DB_FAIL_OPEN=true."
            ).strip()
            if fail_open:
                disable_db(message)
                logger.error("%s Continuing without DB because DB_FAIL_OPEN=true.", message)
                return

            raise RuntimeError(message) from exc

    # Should be unreachable, but keep mypy happy.
    if last_exc is not None:
        raise RuntimeError(f"DB init failed. {describe_database_url()}") from last_exc
