from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.db import db_enabled, session_scope
from app.db_models import Project as ProjectRow
from app.schemas.files import FileItem
from app.schemas.project_files import ProjectFiles, UpdateProjectFilesRequest

router = APIRouter()


def _coerce_file_items(raw: object) -> list[FileItem]:
    if not isinstance(raw, list):
        return []
    items: list[FileItem] = []
    for entry in raw:
        if not isinstance(entry, dict):
            continue
        path = entry.get("path")
        content = entry.get("content")
        if isinstance(path, str) and isinstance(content, str):
            items.append(FileItem(path=path, content=content))
    return items


@router.get("/projects/{project_id}/files", response_model=ProjectFiles)
def get_project_files(project_id: str) -> ProjectFiles:
    if not db_enabled():
        raise HTTPException(status_code=501, detail="Postgres not configured (set DATABASE_URL)")

    with session_scope() as session:
        row = session.get(ProjectRow, project_id)
        if row is None:
            raise HTTPException(status_code=404, detail="Project not found")

        files = _coerce_file_items(getattr(row, "generated_files", None))
        return ProjectFiles(
            project_id=row.id,
            updated_at=row.updated_at,
            files=files,
        )


@router.put("/projects/{project_id}/files", response_model=ProjectFiles)
def put_project_files(project_id: str, body: UpdateProjectFilesRequest) -> ProjectFiles:
    if not db_enabled():
        raise HTTPException(status_code=501, detail="Postgres not configured (set DATABASE_URL)")

    # Basic safety: limit per-file size to avoid accidental huge DB writes.
    # (Postgres can store big JSONB via TOAST, but this keeps the MVP responsive.)
    MAX_FILE_CHARS = 1_000_000

    sanitized: list[dict] = []
    for item in body.files:
        content = item.content
        if len(content) > MAX_FILE_CHARS:
            content = content[:MAX_FILE_CHARS]
        sanitized.append({"path": item.path, "content": content})

    with session_scope() as session:
        row = session.get(ProjectRow, project_id)
        if row is None:
            raise HTTPException(status_code=404, detail="Project not found")

        row.generated_files = sanitized
        session.flush()

        return ProjectFiles(
            project_id=row.id,
            updated_at=row.updated_at,
            files=_coerce_file_items(row.generated_files),
        )
