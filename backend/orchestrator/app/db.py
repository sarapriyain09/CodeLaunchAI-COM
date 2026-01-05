from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Iterator
from urllib.parse import urlparse

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker


_db_forced_disabled: bool = False
_db_forced_disabled_reason: str | None = None


def _truthy_env(name: str, default: str = "false") -> bool:
    return (os.getenv(name, default).strip().lower() in {"1", "true", "yes", "on"})

def _database_url() -> str:
    raw = os.getenv("DATABASE_URL", "").strip()
    if not raw:
        return ""

    # Prefer psycopg (psycopg3). If the user provided a generic URL like
    # postgresql://user:pass@host/db, SQLAlchemy will otherwise default to
    # psycopg2, which we don't ship.
    if raw.startswith("postgresql://") and not raw.startswith("postgresql+psycopg://"):
        return raw.replace("postgresql://", "postgresql+psycopg://", 1)

    return raw


def disable_db(reason: str) -> None:
    """Force-disable DB usage even if DATABASE_URL is set.

    This is meant for fail-open startup behavior when a DB is temporarily
    unavailable or misconfigured.
    """

    global _db_forced_disabled, _db_forced_disabled_reason
    _db_forced_disabled = True
    _db_forced_disabled_reason = (reason or "").strip() or "Database disabled"


# Convenience for local/dev: allow force-disabling DB usage even if DATABASE_URL is set.
if _truthy_env("DB_DISABLE", "false"):
    disable_db("DB disabled by DB_DISABLE=true")


def db_disabled_reason() -> str | None:
    return _db_forced_disabled_reason


def describe_database_url() -> str:
    """Return a safe, redacted description of DATABASE_URL for logs."""

    raw = _database_url()
    if not raw:
        return "DATABASE_URL=<unset>"

    try:
        parsed = urlparse(raw)
        scheme = parsed.scheme or "postgres"
        host = parsed.hostname or ""
        port = f":{parsed.port}" if parsed.port else ""
        dbname = (parsed.path or "").lstrip("/")

        # Never log username/password.
        base = f"{scheme}://"
        if host:
            base += host + port
        else:
            base += "<no-host>"
        if dbname:
            base += f"/{dbname}"
        return f"DATABASE_URL={base}"
    except Exception:
        return "DATABASE_URL=<unparseable>"


def db_enabled() -> bool:
    if _db_forced_disabled:
        return False
    return bool(_database_url())


_engine: Engine | None = None
_SessionLocal: sessionmaker[Session] | None = None


def get_engine() -> Engine:
    global _engine
    if _engine is not None:
        return _engine

    if _db_forced_disabled:
        reason = _db_forced_disabled_reason or "Database disabled"
        raise RuntimeError(f"Database disabled: {reason}")

    database_url = _database_url()
    if not database_url:
        raise RuntimeError("DATABASE_URL is not set")

    _engine = create_engine(
        database_url,
        pool_pre_ping=True,
        future=True,
    )
    return _engine


def get_sessionmaker() -> sessionmaker[Session]:
    global _SessionLocal
    if _SessionLocal is not None:
        return _SessionLocal

    engine = get_engine()
    # We intentionally keep ORM-loaded attributes available after commit.
    # Our `session_scope()` commits on exit even for read-only operations; if
    # `expire_on_commit=True` (default), ORM instances returned from a function
    # become expired and then detached when the session closes, causing
    # DetachedInstanceError when reading attributes.
    _SessionLocal = sessionmaker(
        bind=engine,
        autocommit=False,
        autoflush=False,
        future=True,
        expire_on_commit=False,
    )
    return _SessionLocal


@contextmanager
def session_scope() -> Iterator[Session]:
    SessionLocal = get_sessionmaker()
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
