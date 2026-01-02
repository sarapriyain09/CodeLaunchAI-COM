from __future__ import annotations

from pathlib import Path

import os

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

_DOTENV_PATH = Path(__file__).resolve().parents[1] / '.env'
load_dotenv(dotenv_path=_DOTENV_PATH, override=False)

from app.routes.plan import router as plan_router
from app.routes.chat import router as chat_router
from app.routes.auth import router as auth_router
from app.routes.projects import router as projects_router
from app.routes.generate import router as generate_router
from app.routes.preview import router as preview_router
from app.routes.export import router as export_router
from app.routes.billing import router as billing_router
from app.routes.project_state import router as project_state_router
from app.routes.project_files import router as project_files_router
from app.db_init import init_db

app = FastAPI(title='CodeLaunch Orchestrator', version='0.1.0')


@app.on_event('startup')
def _startup() -> None:
    # Creates tables in Postgres when DATABASE_URL is set.
    init_db()

# Workspace root (…/codelaunchcom). Used to serve public static pages in dev/prod.
_WORKSPACE_ROOT = Path(__file__).resolve().parents[3]

def _parse_cors_origins(raw: str | None) -> list[str]:
    value = (raw or '').strip()
    if not value:
        return ['*']
    return [part.strip() for part in value.split(',') if part.strip()]


cors_origins = _parse_cors_origins(os.getenv('CORS_ALLOW_ORIGINS'))
cors_allow_credentials = (os.getenv('CORS_ALLOW_CREDENTIALS', 'false').strip().lower() == 'true')

# Browsers will reject Access-Control-Allow-Origin: * when credentials are enabled.
if cors_allow_credentials and cors_origins == ['*']:
    cors_allow_credentials = False

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=cors_allow_credentials,
    allow_methods=['*'],
    allow_headers=['*'],
)


@app.get('/health')
def health_check() -> dict[str, bool]:
    return {'ok': True}


@app.get('/', include_in_schema=False)
def public_home() -> FileResponse:
    index_path = _WORKSPACE_ROOT / 'index.html'
    return FileResponse(index_path)


@app.get('/subscribe.html', include_in_schema=False)
def public_subscribe() -> FileResponse:
    subscribe_path = _WORKSPACE_ROOT / 'subscribe.html'
    return FileResponse(subscribe_path)


# Serve the built frontend app from the backend.
# Vite build output goes to workspace_root/app (see frontend/vite.config.ts).
_APP_BUILD_DIR = _WORKSPACE_ROOT / 'app'
if _APP_BUILD_DIR.exists():
    app.mount('/app', StaticFiles(directory=str(_APP_BUILD_DIR), html=True), name='app')


@app.get('/app', include_in_schema=False)
def app_root_redirect() -> RedirectResponse:
    return RedirectResponse(url='/app/')


app.include_router(plan_router)
app.include_router(chat_router)
app.include_router(auth_router)
app.include_router(projects_router)
app.include_router(generate_router)
app.include_router(preview_router, tags=["preview"])
app.include_router(export_router)
app.include_router(billing_router)
app.include_router(project_state_router)
app.include_router(project_files_router)
