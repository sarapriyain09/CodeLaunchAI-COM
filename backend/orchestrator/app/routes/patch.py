from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from pydantic import ValidationError

from app.config import WORKSPACES_DIR
from app.schemas.blueprint import Blueprint
from app.schemas.files import FileItem
from app.services.generator import generate_vite_react_project
from app.services.image_client import maybe_generate_images_and_rewrite_files
from app.services.materializer import ensure_gitignore, write_file_tree
from app.services.planner import patch_blueprint
from app.services.project_files_store import get_project_files_payload, put_project_files_payload
from app.services.project_state_store import get_project_state_payload, put_project_state_payload
from app.services.project_store import touch_project
from app.services.project_store import get_project

router = APIRouter()
logger = logging.getLogger(__name__)


class PatchRequest(BaseModel):
    instruction: str = Field(..., min_length=3, max_length=4000, description="What to change about the app")
    project_name: str = Field("generated-app", min_length=2, max_length=60)


class PatchResponse(BaseModel):
    project_id: str
    changed_paths: List[str]
    removed_paths: List[str]
    file_count: int
    meta: dict = Field(default_factory=dict)


@dataclass(frozen=True)
class _Diff:
    changed: List[str]
    removed: List[str]


def _workspace(project_id: str) -> Path:
    return (WORKSPACES_DIR / project_id).resolve()


def _coerce_file_dicts(raw: object) -> List[dict]:
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


def _files_list_to_map(files: List[dict]) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for item in files:
        p = item.get("path")
        c = item.get("content")
        if isinstance(p, str) and isinstance(c, str):
            out[p] = c
    return out


def _diff_files(old: Dict[str, str], new: Dict[str, str]) -> _Diff:
    changed: List[str] = []
    removed: List[str] = []

    for path, content in new.items():
        if old.get(path) != content:
            changed.append(path)

    for path in old.keys():
        if path not in new:
            removed.append(path)

    changed.sort()
    removed.sort()
    return _Diff(changed=changed, removed=removed)


def _safe_join(base: Path, rel_path: str) -> Path:
    normalized = rel_path.replace('\\', '/').lstrip('/')
    target = (base / normalized).resolve()
    base_resolved = base.resolve()
    if not str(target).startswith(str(base_resolved)):
        raise ValueError(f'Unsafe path detected: {rel_path}')
    return target


def _delete_paths(workspace: Path, paths: List[str]) -> None:
    for rel in paths:
        try:
            target = _safe_join(workspace, rel)
        except ValueError:
            continue
        if target.exists() and target.is_file():
            try:
                target.unlink()
            except Exception:
                continue


def _sanitize_files_for_db(files: Dict[str, str]) -> List[dict]:
    # Keep in sync with project_files.py: limit per-file size.
    MAX_FILE_CHARS = 1_000_000
    out: List[dict] = []
    for path, content in sorted(files.items()):
        if len(content) > MAX_FILE_CHARS:
            content = content[:MAX_FILE_CHARS]
        out.append({"path": path, "content": content})
    return out


def _apply_changed_files(workspace: Path, changed: List[str], files: Dict[str, str]) -> int:
    items: List[FileItem] = []
    for path in changed:
        content = files.get(path)
        if content is None:
            continue
        items.append(FileItem(path=path, content=content))

    if not items:
        workspace.mkdir(parents=True, exist_ok=True)
        ensure_gitignore(workspace)
        return 0

    write_file_tree(workspace, items)
    ensure_gitignore(workspace)
    return len(items)


@router.post('/projects/{project_id}/patch', response_model=PatchResponse)
async def patch_project(project_id: str, body: PatchRequest) -> PatchResponse:
    if get_project(project_id) is None:
        raise HTTPException(status_code=404, detail='Project not found')

    instruction = body.instruction.strip()
    if not instruction:
        raise HTTPException(status_code=400, detail='Missing instruction')

    try:
        touch_project(project_id)

        state_payload = get_project_state_payload(project_id)
        if state_payload is None:
            raise HTTPException(status_code=400, detail='No blueprint found for this project yet. Run Generate at least once before Update.')

        _updated_at, blueprint_blob, plan_blob = state_payload
        try:
            existing_blueprint = Blueprint.model_validate(blueprint_blob or {})
        except ValidationError as exc:
            raise HTTPException(
                status_code=400,
                detail='No blueprint found for this project yet. Run Generate at least once before Update.',
            ) from exc

        new_blueprint, debug = await patch_blueprint(existing_blueprint, instruction)

        # Generate the next full file set.
        files = await generate_vite_react_project(new_blueprint, body.project_name)

        workspace = _workspace(project_id)
        files, generated_seeds = await maybe_generate_images_and_rewrite_files(
            files=files,
            workspace=workspace,
            product_name=new_blueprint.branding.product_name,
            theme_style=new_blueprint.theme.style,
        )

        files_payload = get_project_files_payload(project_id)
        old_files_list = []
        if files_payload is not None:
            _files_updated_at, old_files_list = files_payload
        old_files_list = _coerce_file_dicts(old_files_list)
        old_files_map = _files_list_to_map(old_files_list)

        diff = _diff_files(old_files_map, files)

        # Persist new blueprint + files.
        if not isinstance(plan_blob, dict):
            plan_blob = {}
        patch_log = plan_blob.get('patches')
        if not isinstance(patch_log, list):
            patch_log = []
        patch_log.append({'instruction': instruction[:2000]})
        plan_blob['patches'] = patch_log[-20:]

        put_project_state_payload(
            project_id,
            blueprint=new_blueprint.model_dump(mode='json'),
            plan=plan_blob,
        )
        put_project_files_payload(project_id, _sanitize_files_for_db(files))

        # Apply only changed files into the existing workspace, and delete removed ones.
        workspace = _workspace(project_id)
        applied = _apply_changed_files(workspace, diff.changed, files)
        _delete_paths(workspace, diff.removed)

        if generated_seeds:
            logger.info(
                'Patch generated %d images for project_id=%s (seeds=%s)',
                len(generated_seeds),
                project_id,
                generated_seeds,
            )

        return PatchResponse(
            project_id=project_id,
            changed_paths=diff.changed,
            removed_paths=diff.removed,
            file_count=applied,
            meta={
                'blueprint_attempts': debug.get('attempts'),
                'offline': bool(debug.get('offline')),
            },
        )
    except HTTPException:
        raise
    except Exception as error:
        logger.exception('Patch failed for project_id=%s', project_id)
        raise HTTPException(status_code=400, detail=f'Patch failed: {error}') from error
