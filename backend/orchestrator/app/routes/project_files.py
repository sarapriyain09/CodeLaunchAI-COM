from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

from app.schemas.files import FileItem
from app.schemas.project_files import ProjectFiles, UpdateProjectFilesRequest
from app.services.project_files_store import get_project_files_payload, put_project_files_payload
from app.services.project_store import get_project

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
    if get_project(project_id) is None:
        raise HTTPException(status_code=404, detail="Project not found")

    payload = get_project_files_payload(project_id)
    if payload is None:
        return ProjectFiles(
            project_id=project_id,
            updated_at=datetime.now(timezone.utc),
            files=[],
        )

    updated_at, raw_files = payload
    return ProjectFiles(
        project_id=project_id,
        updated_at=updated_at,
        files=_coerce_file_items(raw_files),
    )


@router.put("/projects/{project_id}/files", response_model=ProjectFiles)
def put_project_files(project_id: str, body: UpdateProjectFilesRequest) -> ProjectFiles:
    if get_project(project_id) is None:
        raise HTTPException(status_code=404, detail="Project not found")

    sanitized: list[dict] = [{"path": f.path, "content": f.content} for f in body.files]

    try:
        updated_at, raw_files = put_project_files_payload(project_id, sanitized)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

    return ProjectFiles(
        project_id=project_id,
        updated_at=updated_at,
        files=_coerce_file_items(raw_files),
    )
