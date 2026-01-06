from __future__ import annotations

import json
import os
import re
import shutil
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select

from app.config import WORKSPACES_DIR
from app.db import db_enabled, session_scope
from app.db_models import Project as ProjectRow, ProjectChatMessage as ProjectChatMessageRow, ProjectOwner as ProjectOwnerRow
from app.schemas.projects import Project


_PROJECT_ID_RE = re.compile(r"^p_[A-Za-z0-9_-]{6,}$")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _db_path() -> Path:
    WORKSPACES_DIR.mkdir(parents=True, exist_ok=True)
    return (WORKSPACES_DIR / "_projects.json").resolve()


def _workspace_path(project_id: str) -> Path:
    WORKSPACES_DIR.mkdir(parents=True, exist_ok=True)
    candidate = (WORKSPACES_DIR / project_id).resolve()
    base = WORKSPACES_DIR.resolve()
    if not str(candidate).startswith(str(base)):
        raise ValueError("Invalid project workspace path")
    return candidate


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


def _delete_workspace(project_id: str) -> None:
    try:
        workspace = _workspace_path(project_id)
    except ValueError:
        return
    if workspace.exists():
        shutil.rmtree(workspace, ignore_errors=True)


def list_projects(*, owner_key: str) -> list[Project]:
    if db_enabled():
        with session_scope() as session:
            rows = (
                session.execute(
                    select(ProjectRow)
                    .join(ProjectOwnerRow, ProjectOwnerRow.project_id == ProjectRow.id)
                    .where(ProjectOwnerRow.owner_key == owner_key)
                    .order_by(ProjectRow.updated_at.desc())
                )
                .scalars()
                .all()
            )
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
            if isinstance(raw, dict) and raw.get("owner") != owner_key:
                continue
            out.append(Project.model_validate(raw))
        except Exception:
            continue
    # newest first
    out.sort(key=lambda p: p.updated_at, reverse=True)
    return out


def get_project(*, owner_key: str, project_id: str) -> Project | None:
    if db_enabled():
        with session_scope() as session:
            owner = session.get(ProjectOwnerRow, project_id)
            if owner is None or owner.owner_key != owner_key:
                return None
            row = session.get(ProjectRow, project_id)
            if row is None:
                return None
            return Project(
                id=row.id,
                name=row.name,
                created_at=row.created_at,
                updated_at=row.updated_at,
            )

    for project in list_projects(owner_key=owner_key):
        if project.id == project_id:
            return project
    return None


def _make_default_name(existing_count: int) -> str:
    return f"Project {existing_count + 1}"


def _owner_unlimited(owner_key: str) -> bool:
    # Local dev: always unlimited.
    if owner_key.startswith("anon:127.0.0.1") or owner_key.startswith("anon:::1"):
        return True

    allow_keys = {
        e.strip()
        for e in (os.getenv("UNLIMITED_PROJECT_OWNER_KEYS", "") or "").split(",")
        if e.strip()
    }
    if owner_key in allow_keys:
        return True

    if owner_key.startswith("anon:"):
        ip = owner_key.split(":", 1)[1].strip()
        allow_ips = {
            e.strip()
            for e in (os.getenv("UNLIMITED_PROJECT_IPS", "") or "").split(",")
            if e.strip()
        }
        if ip and ip in allow_ips:
            return True

    return False


def _max_projects_for_owner(owner_key: str) -> int:
    if _owner_unlimited(owner_key):
        return 0
    raw = os.getenv("MAX_PROJECTS_PER_OWNER", "1")
    try:
        return max(0, int(str(raw).strip()))
    except Exception:
        return 1


def create_project(*, owner_key: str, name: str | None = None, project_id: str | None = None) -> Project:
    if project_id is not None:
        project_id = project_id.strip()
        if not _PROJECT_ID_RE.match(project_id):
            raise ValueError("Invalid project_id; expected like p_<uuid>")

    now = _utcnow()
    current = list_projects(owner_key=owner_key)

    if project_id is None:
        project_id = f"p_{uuid.uuid4().hex}"

    if any(p.id == project_id for p in current):
        # idempotent create: return existing
        existing = next(p for p in current if p.id == project_id)
        return existing

    limit = _max_projects_for_owner(owner_key)
    if limit > 0 and len(current) >= limit:
        raise ValueError("Project limit reached for this user. Please delete your existing project to create a new one.")

    safe_name = (name or "").strip() or _make_default_name(len(current))

    project = Project(
        id=project_id,
        name=safe_name,
        created_at=now,
        updated_at=now,
    )

    if db_enabled():
        with session_scope() as session:
            existing_owner = session.get(ProjectOwnerRow, project_id)
            if existing_owner is not None:
                if existing_owner.owner_key != owner_key:
                    raise ValueError("Project id already exists")

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
            session.add(ProjectOwnerRow(project_id=project_id, owner_key=owner_key))
            session.flush()
            return Project(
                id=row.id,
                name=row.name,
                created_at=row.created_at,
                updated_at=row.updated_at,
            )

    # persist (JSON)
    db = _load()
    existing = db.get("projects", [])
    if not isinstance(existing, list):
        existing = []

    # Keep other owners' records intact.
    others: list = []
    for entry in existing:
        if isinstance(entry, dict) and entry.get("owner") == owner_key:
            continue
        others.append(entry)

    record = project.model_dump(mode="json")
    record["owner"] = owner_key
    db["projects"] = others + [p.model_dump(mode="json") | {"owner": owner_key} for p in current] + [record]
    _atomic_write(_db_path(), db)

    return project


def touch_project(*, owner_key: str, project_id: str) -> None:
    if db_enabled():
        with session_scope() as session:
            owner = session.get(ProjectOwnerRow, project_id)
            if owner is None or owner.owner_key != owner_key:
                return
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
        if isinstance(p, dict) and p.get("id") == project_id and p.get("owner") == owner_key:
            p["updated_at"] = now
            changed = True
            break

    if changed:
        _atomic_write(_db_path(), {"projects": projects})


def delete_project(*, owner_key: str, project_id: str) -> bool:
    """Remove a project record and its generated workspace."""

    if db_enabled():
        with session_scope() as session:
            owner = session.get(ProjectOwnerRow, project_id)
            if owner is None or owner.owner_key != owner_key:
                return False
            project = session.get(ProjectRow, project_id)
            if project is None:
                return False
            session.query(ProjectChatMessageRow).filter(ProjectChatMessageRow.project_id == project_id).delete()
            session.delete(owner)
            session.delete(project)
            session.flush()
    else:
        data = _load()
        projects = data.get("projects", [])
        filtered: list = []
        removed = False
        for entry in projects:
            if isinstance(entry, dict) and entry.get("id") == project_id and entry.get("owner") == owner_key:
                removed = True
                continue
            filtered.append(entry)
        if not removed:
            return False
        _atomic_write(_db_path(), {"projects": filtered})

    _delete_workspace(project_id)
    return True
