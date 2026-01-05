from __future__ import annotations

import logging
import re
import time
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
from pydantic import BaseModel, Field

from app.config import WORKSPACES_DIR
from app.schemas.blueprint import Blueprint
from app.schemas.files import FileItem
from app.services.generator import generate_vite_react_project
from app.services.materializer import ensure_gitignore, write_file_tree
from app.services.builder import BuildError, clean_dist, npm_build, npm_install_if_needed
from app.services.stream_runner import (
    node_modules_ready_for_build,
    stream_npm_build,
    stream_npm_install,
)
from app.services.image_client import maybe_generate_images_and_rewrite_files
from app.services.project_files_store import get_project_files_payload
from app.services.project_store import touch_project

router = APIRouter()
logger = logging.getLogger(__name__)


_ASSET_PREFIX_RE = re.compile(r'(?P<q>["\"])\/assets\/', re.IGNORECASE)


def _rewrite_index_asset_paths(html: str, project_id: str) -> str:
    """Rewrite absolute Vite asset paths so previews work under /preview/{project_id}/.

    Many Vite builds emit <script src="/assets/..."> which breaks when the app is served
    from a subpath (our preview is /preview/{project_id}/). We rewrite to a project-scoped
    asset path handled by preview_assets.
    """
    return _ASSET_PREFIX_RE.sub(lambda m: f"{m.group('q')}/preview/{project_id}/assets/", html)


class MaterializeRequest(BaseModel):
    blueprint: Blueprint
    project_name: str = Field('generated-app', min_length=2, max_length=60)


class MaterializeResponse(BaseModel):
    project_id: str
    workspace_path: str
    file_count: int


class BuildResponse(BaseModel):
    project_id: str
    installed: str
    built: str
    preview_url: str


def _workspace(project_id: str) -> Path:
    return (WORKSPACES_DIR / project_id).resolve()


def _dist_dir(project_id: str) -> Path:
    return _workspace(project_id) / 'dist'


def _ensure_materialized_workspace(project_id: str, workspace: Path) -> None:
    """Ensure the on-disk workspace contains a buildable Vite app.

    Some flows persist project files/state into the store (which creates the project
    directory) without writing the full file tree to disk. In that case, the workspace
    folder exists but critical files like package.json are missing, causing npm to fail
    with ENOENT.
    """

    package_json = workspace / 'package.json'
    if package_json.exists():
        return

    payload = get_project_files_payload(project_id)
    if payload is None:
        raise HTTPException(status_code=404, detail='Workspace not materialized yet; generate/materialize first.')

    _updated_at, raw_files = payload
    if not raw_files:
        raise HTTPException(status_code=404, detail='Workspace not materialized yet; generate/materialize first.')

    file_items = [FileItem(path=f.get('path', ''), content=f.get('content', '')) for f in raw_files]
    # Only write entries that look like valid file items.
    file_items = [fi for fi in file_items if fi.path and isinstance(fi.path, str) and isinstance(fi.content, str)]
    if not file_items:
        raise HTTPException(status_code=404, detail='Workspace not materialized yet; generate/materialize first.')

    write_file_tree(workspace, file_items)
    ensure_gitignore(workspace)


def sse_event(event: str, data: str) -> str:
    lines = data.splitlines() or ['']
    payload = f'event: {event}\n'
    payload += '\n'.join([f'data: {line}' for line in lines])
    return payload + '\n\n'


@router.post('/projects/{project_id}/materialize', response_model=MaterializeResponse)
async def materialize_project(project_id: str, body: MaterializeRequest) -> MaterializeResponse:
    try:
        touch_project(project_id)
        workspace = _workspace(project_id)
        files = await generate_vite_react_project(body.blueprint, body.project_name)

        # Optional: generate real PNGs via OpenAI Images and rewrite TSX to use them.
        # Controlled via backend/orchestrator/.env: GENERATE_IMAGES=true
        files, generated_seeds = await maybe_generate_images_and_rewrite_files(
            files=files,
            workspace=workspace,
            product_name=body.blueprint.branding.product_name,
            theme_style=body.blueprint.theme.style,
        )

        file_items = [FileItem(path=path, content=content) for path, content in files.items()]
        write_file_tree(workspace, file_items)
        ensure_gitignore(workspace)
        if generated_seeds:
            logger.info('Generated %d images for project_id=%s (seeds=%s)', len(generated_seeds), project_id, generated_seeds)
        return MaterializeResponse(
            project_id=project_id,
            workspace_path=str(workspace),
            file_count=len(file_items),
        )
    except Exception as error:
        logger.exception('Materialize failed for project_id=%s project_name=%s', project_id, body.project_name)
        raise HTTPException(status_code=400, detail=f'Materialize failed: {error}') from error


@router.post('/projects/{project_id}/build', response_model=BuildResponse)
async def build_project(project_id: str) -> BuildResponse:
    workspace = _workspace(project_id)
    if not workspace.exists():
        raise HTTPException(status_code=404, detail='Workspace not found; generate/materialize first.')

    _ensure_materialized_workspace(project_id, workspace)

    touch_project(project_id)

    try:
        clean_dist(workspace)
        install_out = npm_install_if_needed(workspace)
        build_out = npm_build(workspace)
    except BuildError as error:
        raise HTTPException(status_code=400, detail=f'Build failed:\n{error}') from error

    dist = _dist_dir(project_id)
    if not dist.exists():
        raise HTTPException(status_code=500, detail='Build finished but dist/ missing.')

    return BuildResponse(
        project_id=project_id,
        installed=install_out,
        built=build_out,
        preview_url=f'/preview/{project_id}/',
    )


@router.get('/preview/{project_id}/', response_class=HTMLResponse)
async def preview_index(project_id: str) -> HTMLResponse:
    dist = _dist_dir(project_id)
    index = dist / 'index.html'
    if not index.exists():
        raise HTTPException(status_code=404, detail='Preview not built yet.')
    html = index.read_text(encoding='utf-8')
    html = _rewrite_index_asset_paths(html, project_id)
    return HTMLResponse(html)


@router.get('/preview/{project_id}/{asset_path:path}')
async def preview_assets(project_id: str, asset_path: str):
    dist = _dist_dir(project_id)
    target = (dist / asset_path).resolve()
    if not str(target).startswith(str(dist.resolve())):
        raise HTTPException(status_code=400, detail='Invalid asset path.')
    if not target.exists():
        index = dist / 'index.html'
        if index.exists():
            html = index.read_text(encoding='utf-8')
            html = _rewrite_index_asset_paths(html, project_id)
            return HTMLResponse(html)
        raise HTTPException(status_code=404, detail='File not found.')
    return FileResponse(str(target))


@router.get('/assets/{asset_path:path}')
async def preview_assets_root(asset_path: str, request: Request):
    """Compatibility route for builds that still request /assets/* from domain root.

    We attempt to infer the project_id from the Referer header (which should be a
    /preview/{project_id}/ URL) and serve the correct file.
    """

    referer = request.headers.get('referer') or request.headers.get('referrer') or ''
    match = re.search(r'/preview/(?P<pid>[^/]+)/', referer)
    if not match:
        raise HTTPException(status_code=404, detail='Unknown preview context for /assets request.')

    project_id = match.group('pid')
    dist = _dist_dir(project_id)
    target = (dist / 'assets' / asset_path).resolve()
    if not str(target).startswith(str(dist.resolve())):
        raise HTTPException(status_code=400, detail='Invalid asset path.')
    if not target.exists():
        raise HTTPException(status_code=404, detail='Asset not found.')
    return FileResponse(str(target))


@router.get('/projects/{project_id}/build/stream')
async def build_stream(project_id: str, install: bool = True):
    workspace = _workspace(project_id)
    if not workspace.exists():
        raise HTTPException(status_code=404, detail='Workspace not found. Generate/materialize first.')

    def generator():
        yield sse_event('status', 'Build started')
        yield sse_event('log', f'Workspace: {workspace}')

        last_ping = time.time()

        def maybe_ping() -> str | None:
            nonlocal last_ping
            now = time.time()
            if now - last_ping >= 15:
                last_ping = now
                return sse_event('status', 'ping')
            return None

        try:
            _ensure_materialized_workspace(project_id, workspace)
            clean_dist(workspace)
            yield sse_event('log', 'Cleaned dist/')
            ping = maybe_ping()
            if ping:
                yield ping

            if install:
                if node_modules_ready_for_build(workspace):
                    yield sse_event('log', 'node_modules exists. Skipping npm install.')
                else:
                    for line in stream_npm_install(workspace):
                        yield sse_event('log', line.rstrip('\n'))
                        ping = maybe_ping()
                        if ping:
                            yield ping

            for line in stream_npm_build(workspace):
                yield sse_event('log', line.rstrip('\n'))
                ping = maybe_ping()
                if ping:
                    yield ping

            dist = _dist_dir(project_id)
            if not dist.exists():
                raise RuntimeError('Build finished but dist/ not found.')

            yield sse_event('done', f'/preview/{project_id}/')
        except Exception as error:  # pragma: no cover - surfaced to client
            yield sse_event('error', str(error)[:1000])

        yield sse_event('status', 'Build stream ended')

    return StreamingResponse(
        generator(),
        media_type='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'X-Accel-Buffering': 'no',
        },
    )