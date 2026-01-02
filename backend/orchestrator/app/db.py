from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

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


def db_enabled() -> bool:
    return bool(_database_url())


_engine: Engine | None = None
_SessionLocal: sessionmaker[Session] | None = None


def get_engine() -> Engine:
    global _engine
    if _engine is not None:
        return _engine

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
    _SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)
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
