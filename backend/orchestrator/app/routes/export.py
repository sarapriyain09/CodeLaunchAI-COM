from __future__ import annotations

import io
import zipfile
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from app.config import WORKSPACES_DIR
from app.schemas.auth import UserPublic
from app.services.auth import require_user
from app.services.subscription import is_subscribed, is_subscription_required


router = APIRouter()


def _workspace(project_id: str) -> Path:
    return (WORKSPACES_DIR / project_id).resolve()


def _zip_dir_to_bytes(root: Path) -> io.BytesIO:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED) as z:
        for path in root.rglob("*"):
            if path.is_dir():
                continue
            rel = path.relative_to(root)
            # Keep zip paths normalized to forward slashes
            z.write(path, arcname=str(rel).replace("\\", "/"))
    buf.seek(0)
    return buf


@router.get("/projects/{project_id}/export.zip")
def export_project_zip(project_id: str, request: Request) -> StreamingResponse:
    # Export can be configured as free (no auth) for MVP demos.
    # If subscription is required, enforce auth + subscription gating.
    if is_subscription_required():
        user: UserPublic = require_user(request)

        if not is_subscribed(user):
            # 402 Payment Required is appropriate for subscription gating
            raise HTTPException(status_code=402, detail="Subscription required to download")

    workspace = _workspace(project_id)
    if not workspace.exists():
        raise HTTPException(status_code=404, detail="Workspace not found; generate first")

    buf = _zip_dir_to_bytes(workspace)

    filename = f"{project_id}.zip"
    headers = {"Content-Disposition": f"attachment; filename=\"{filename}\""}

    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers=headers,
    )
