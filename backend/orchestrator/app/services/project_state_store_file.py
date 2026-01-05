from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.config import WORKSPACES_DIR


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _state_path(project_id: str) -> Path:
    WORKSPACES_DIR.mkdir(parents=True, exist_ok=True)
    return (WORKSPACES_DIR / project_id / "_state.json").resolve()


def _ensure_project_dir(project_id: str) -> Path:
    WORKSPACES_DIR.mkdir(parents=True, exist_ok=True)
    d = (WORKSPACES_DIR / project_id).resolve()
    d.mkdir(parents=True, exist_ok=True)
    return d


def get_state(project_id: str) -> dict[str, Any] | None:
    path = _state_path(project_id)
    if not path.exists():
        return None

    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None

    if not isinstance(raw, dict):
        return None

    return raw


def put_state(project_id: str, *, blueprint: dict | None = None, plan: dict | None = None) -> dict[str, Any]:
    _ensure_project_dir(project_id)

    current = get_state(project_id) or {}

    next_state: dict[str, Any] = {
        "project_id": project_id,
        "updated_at": _utcnow().isoformat(),
        "blueprint": current.get("blueprint") if isinstance(current.get("blueprint"), dict) else {},
        "plan": current.get("plan") if isinstance(current.get("plan"), dict) else {},
    }

    if blueprint is not None:
        next_state["blueprint"] = blueprint
    if plan is not None:
        next_state["plan"] = plan

    path = _state_path(project_id)
    path.write_text(json.dumps(next_state, ensure_ascii=False, indent=2), encoding="utf-8")
    return next_state
