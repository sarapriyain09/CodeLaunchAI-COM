from __future__ import annotations

from datetime import datetime
from typing import List, Tuple

from app.db import db_enabled, session_scope
from app.db_models import Project as ProjectRow
from app.services import project_files_store_file


def _coerce_file_items(raw: object) -> List[dict]:
    if not isinstance(raw, list):
        return []
    out: List[dict] = []
    for entry in raw:
        if not isinstance(entry, dict):
            continue
        p = entry.get("path")
        c = entry.get("content")
        if isinstance(p, str) and isinstance(c, str):
            out.append({"path": p, "content": c})
    return out


def get_project_files_payload(project_id: str) -> Tuple[datetime, List[dict]] | None:
    if db_enabled():
        with session_scope() as session:
            row = session.get(ProjectRow, project_id)
            if row is None:
                return None
            updated_at = row.updated_at
            files = _coerce_file_items(getattr(row, "generated_files", None))
            return updated_at, files

    raw = project_files_store_file.get_files(project_id)
    if not raw:
        return None

    updated_at_str = raw.get("updated_at")
    files = _coerce_file_items(raw.get("files"))
    try:
        updated_at = datetime.fromisoformat(updated_at_str) if isinstance(updated_at_str, str) else datetime.utcnow()
    except Exception:
        updated_at = datetime.utcnow()

    return updated_at, files


def put_project_files_payload(project_id: str, files: List[dict]) -> Tuple[datetime, List[dict]]:
    if db_enabled():
        with session_scope() as session:
            row = session.get(ProjectRow, project_id)
            if row is None:
                raise ValueError("Project not found")
            row.generated_files = files
            session.flush()
            return row.updated_at, _coerce_file_items(row.generated_files)

    raw = project_files_store_file.put_files(project_id, files)
    updated_at_str = raw.get("updated_at")
    try:
        updated_at = datetime.fromisoformat(updated_at_str) if isinstance(updated_at_str, str) else datetime.utcnow()
    except Exception:
        updated_at = datetime.utcnow()

    return updated_at, _coerce_file_items(raw.get("files"))
