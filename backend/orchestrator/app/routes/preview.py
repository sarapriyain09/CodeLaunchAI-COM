from __future__ import annotations

import logging
import re
import time
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse, StreamingResponse
from pydantic import BaseModel, Field

from app.config import PUBLIC_APP_ORIGIN, WORKSPACES_DIR
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
_REL_ASSET_PREFIX_RE = re.compile(r'(?P<q>["\"])\.\/assets\/', re.IGNORECASE)


def _rewrite_index_asset_paths(html: str, base_path: str) -> str:
    """Rewrite absolute Vite asset paths so previews work under a subpath.

    Many Vite builds emit <script src="/assets/..."> which breaks when the app is served
    from a subpath (e.g. /preview/{project_id}/ or /p/{project_id}/). We rewrite to a
    project-scoped asset path handled by our preview asset routes.
    """

    if not base_path.endswith('/'):
        base_path = f"{base_path}/"

    # Handle both absolute and relative asset URLs emitted by Vite.
    # - src="/assets/..." (absolute)
    # - src="./assets/..." (relative; breaks when the page URL has no trailing slash)
    html = _ASSET_PREFIX_RE.sub(lambda m: f"{m.group('q')}{base_path}assets/", html)
    html = _REL_ASSET_PREFIX_RE.sub(lambda m: f"{m.group('q')}{base_path}assets/", html)
    return html


def _preview_index_html(project_id: str, mount: str) -> HTMLResponse:
    dist = _dist_dir(project_id)
    index = dist / 'index.html'
    if not index.exists():
        html = (
            "<!doctype html>"
            "<html><head><meta charset='utf-8'/>"
            "<meta name='viewport' content='width=device-width, initial-scale=1'/>"
            "<title>Preview not built</title>"
            "</head><body style='font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif; padding: 24px;'>"
            f"<h1 style='margin: 0 0 8px;'>Preview not built yet</h1>"
            f"<p style='margin: 0 0 16px;'>Project: <code>{project_id}</code></p>"
            "<p style='margin: 0 0 16px;'>Go back to the workspace and click <b>Generate</b> (first build) or <b>Update</b> (rebuild). "
            "Then reopen this preview.</p>"
            "</body></html>"
        )
        return HTMLResponse(html, status_code=404)

    html = index.read_text(encoding='utf-8')
    html = _rewrite_index_asset_paths(html, f"/{mount}/{project_id}/")
    return HTMLResponse(html)


def _maybe_redirect_to_public_origin(request: Request, project_id: str) -> RedirectResponse | None:
    if not PUBLIC_APP_ORIGIN:
        return None
    host = (request.url.hostname or '').lower()
    if host.endswith('onrender.com'):
        return RedirectResponse(f"{PUBLIC_APP_ORIGIN}/previews/{project_id}", status_code=302)
    return None


def _preview_asset_response(project_id: str, asset_path: str, mount: str):
    dist = _dist_dir(project_id)
    target = (dist / asset_path).resolve()
    if not str(target).startswith(str(dist.resolve())):
        raise HTTPException(status_code=400, detail='Invalid asset path.')
    if not target.exists():
        index = dist / 'index.html'
        if index.exists():
            html = index.read_text(encoding='utf-8')
            html = _rewrite_index_asset_paths(html, f"/{mount}/{project_id}/")
            return HTMLResponse(html)
        raise HTTPException(status_code=404, detail='File not found.')
    return FileResponse(str(target))


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
        preview_url=f'/previews/{project_id}',
    )


@router.get('/preview/{project_id}/', response_class=HTMLResponse)
async def preview_index(project_id: str, request: Request) -> HTMLResponse:
    redirect = _maybe_redirect_to_public_origin(request, project_id)
    if redirect:
        return redirect
    return _preview_index_html(project_id, mount='preview')


@router.get('/p/{project_id}/', response_class=HTMLResponse)
async def public_preview_index(project_id: str, request: Request) -> HTMLResponse:
    """Public-domain-friendly alias for preview.

    Some hosts (notably Vercel) may treat /preview/* specially. We provide /p/* as a stable
    alias so the frontend can open previews under the main domain without warnings.
    """

    redirect = _maybe_redirect_to_public_origin(request, project_id)
    if redirect:
        return redirect
    return _preview_index_html(project_id, mount='p')


@router.get('/p/{project_id}', response_class=HTMLResponse, include_in_schema=False)
async def public_preview_index_noslash(project_id: str, request: Request) -> HTMLResponse:
    redirect = _maybe_redirect_to_public_origin(request, project_id)
    if redirect:
        return redirect
    return _preview_index_html(project_id, mount='p')


@router.get('/previews/{project_id}/', response_class=HTMLResponse)
async def public_previews_index(project_id: str, request: Request) -> HTMLResponse:
    """Second public-domain-friendly alias for preview.

    Some hosts may treat short paths like /p/* or /preview/* specially. Provide a
    longer, explicit path that is unlikely to collide with platform routing.
    """

    redirect = _maybe_redirect_to_public_origin(request, project_id)
    if redirect:
        return redirect
    return _preview_index_html(project_id, mount='previews')


@router.get('/previews/{project_id}', response_class=HTMLResponse, include_in_schema=False)
async def public_previews_index_noslash(project_id: str, request: Request) -> HTMLResponse:
    redirect = _maybe_redirect_to_public_origin(request, project_id)
    if redirect:
        return redirect
    return _preview_index_html(project_id, mount='previews')


@router.get('/preview/{project_id}/{asset_path:path}')
async def preview_assets(project_id: str, asset_path: str):
    return _preview_asset_response(project_id, asset_path, mount='preview')


@router.get('/p/{project_id}/{asset_path:path}')
async def public_preview_assets(project_id: str, asset_path: str):
    return _preview_asset_response(project_id, asset_path, mount='p')


@router.get('/previews/{project_id}/{asset_path:path}')
async def public_previews_assets(project_id: str, asset_path: str):
    return _preview_asset_response(project_id, asset_path, mount='previews')


@router.get('/assets/{asset_path:path}')
async def preview_assets_root(asset_path: str, request: Request):
    """Compatibility route for builds that still request /assets/* from domain root.

    We attempt to infer the project_id from the Referer header (which should be a
    /preview/{project_id}/ URL) and serve the correct file.
    """

    referer = request.headers.get('referer') or request.headers.get('referrer') or ''
    match = re.search(r'/(?:preview|p|previews)/(?P<pid>[^/]+)/', referer)
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

            yield sse_event('done', f'/previews/{project_id}')
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