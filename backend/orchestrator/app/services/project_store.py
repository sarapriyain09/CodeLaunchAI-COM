from __future__ import annotations

import json
import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select

from app.config import WORKSPACES_DIR
from app.db import db_enabled, session_scope
from app.db_models import Project as ProjectRow
from app.schemas.projects import Project


_PROJECT_ID_RE = re.compile(r"^p_[A-Za-z0-9_-]{6,}$")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _db_path() -> Path:
    WORKSPACES_DIR.mkdir(parents=True, exist_ok=True)
    return (WORKSPACES_DIR / "_projects.json").resolve()


def _load() -> dict:
    path = _db_path()
    if not path.exists():
        return {"projects": []}

    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, dict):
        return {"projects": []}

    projects = data.get("projects")
    if not isinstance(projects, list):
        return {"projects": []}

    return {"projects": projects}


def _atomic_write(path: Path, payload: dict) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    tmp.replace(path)


def list_projects() -> list[Project]:
    if db_enabled():
        with session_scope() as session:
            rows = session.execute(select(ProjectRow).order_by(ProjectRow.updated_at.desc())).scalars().all()
            return [
                Project(
                    id=r.id,
                    name=r.name,
                    created_at=r.created_at,
                    updated_at=r.updated_at,
                )
                for r in rows
            ]

    data = _load()
    out: list[Project] = []
    for raw in data["projects"]:
        try:
            out.append(Project.model_validate(raw))
        except Exception:
            continue
    # newest first
    out.sort(key=lambda p: p.updated_at, reverse=True)
    return out


def get_project(project_id: str) -> Project | None:
    if db_enabled():
        with session_scope() as session:
            row = session.get(ProjectRow, project_id)
            if row is None:
                return None
            return Project(
                id=row.id,
                name=row.name,
                created_at=row.created_at,
                updated_at=row.updated_at,
            )

    for project in list_projects():
        if project.id == project_id:
            return project
    return None


def _make_default_name(existing_count: int) -> str:
    return f"Project {existing_count + 1}"


def create_project(name: str | None = None, project_id: str | None = None) -> Project:
    if project_id is not None:
        project_id = project_id.strip()
        if not _PROJECT_ID_RE.match(project_id):
            raise ValueError("Invalid project_id; expected like p_<uuid>")

    now = _utcnow()
    current = list_projects()

    if project_id is None:
        project_id = f"p_{uuid.uuid4().hex}"

    if any(p.id == project_id for p in current):
        # idempotent create: return existing
        existing = next(p for p in current if p.id == project_id)
        return existing

    safe_name = (name or "").strip() or _make_default_name(len(current))

    project = Project(
        id=project_id,
        name=safe_name,
        created_at=now,
        updated_at=now,
    )

    if db_enabled():
        with session_scope() as session:
            existing = session.get(ProjectRow, project_id)
            if existing is not None:
                return Project(
                    id=existing.id,
                    name=existing.name,
                    created_at=existing.created_at,
                    updated_at=existing.updated_at,
                )
            row = ProjectRow(id=project_id, name=safe_name)
            session.add(row)
            session.flush()
            return Project(
                id=row.id,
                name=row.name,
                created_at=row.created_at,
                updated_at=row.updated_at,
            )

    # persist
    db = _load()
    db["projects"] = [p.model_dump(mode="json") for p in current] + [project.model_dump(mode="json")]
    _atomic_write(_db_path(), db)

    return project


def touch_project(project_id: str) -> None:
    if db_enabled():
        with session_scope() as session:
            row = session.get(ProjectRow, project_id)
            if row is None:
                return
            row.updated_at = _utcnow()
            session.flush()
            return

    data = _load()
    projects = data.get("projects", [])
    now = _utcnow().isoformat()

    changed = False
    for p in projects:
        if isinstance(p, dict) and p.get("id") == project_id:
            p["updated_at"] = now
            changed = True
            break

    if changed:
        _atomic_write(_db_path(), {"projects": projects})
