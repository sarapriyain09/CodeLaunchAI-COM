from __future__ import annotations

from sqlalchemy import text

from app.db import db_enabled, get_engine
from app.db_models import Base


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
