from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from app.config import WORKSPACES_DIR


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _files_path(project_id: str) -> Path:
    WORKSPACES_DIR.mkdir(parents=True, exist_ok=True)
    return (WORKSPACES_DIR / project_id / "_files.json").resolve()


def _ensure_project_dir(project_id: str) -> Path:
    WORKSPACES_DIR.mkdir(parents=True, exist_ok=True)
    d = (WORKSPACES_DIR / project_id).resolve()
    d.mkdir(parents=True, exist_ok=True)
    return d


def get_files(project_id: str) -> dict[str, Any] | None:
    path = _files_path(project_id)
    if not path.exists():
        return None

    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None

    if not isinstance(raw, dict):
        return None

    return raw


def put_files(project_id: str, files: List[dict]) -> dict[str, Any]:
    _ensure_project_dir(project_id)

    # Safety: limit per-file size
    MAX_FILE_CHARS = 1_000_000
    sanitized: List[dict] = []
    for entry in files:
        if not isinstance(entry, dict):
            continue
        p = entry.get("path")
        c = entry.get("content")
        if not isinstance(p, str) or not isinstance(c, str):
            continue
        if len(c) > MAX_FILE_CHARS:
            c = c[:MAX_FILE_CHARS]
        sanitized.append({"path": p, "content": c})

    payload: Dict[str, Any] = {
        "project_id": project_id,
        "updated_at": _utcnow().isoformat(),
        "files": sanitized,
    }

    path = _files_path(project_id)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload
