# Frontend (Vite build output served by backend)

This repo runs in **backend-only mode**:

- The FastAPI backend serves the public site at `/`.
- The built React app is served by the backend at `/app/`.
- Subscription/registration is served as a public HTML page at `/subscribe.html`.

Important: the Vite dev server is intentionally disabled. Use `vite build --watch` instead.

## URLs

- Public home: `http://127.0.0.1:7080/`
- Subscribe: `http://127.0.0.1:7080/subscribe.html`
- App: `http://127.0.0.1:7080/app/#/builder`

## Run (recommended)

Use the VS Code task:

- Run Task → **Backend-only: run everything (backend + build-watch)**

This starts:

- FastAPI via uvicorn on `127.0.0.1:7080`
- `vite build --watch` outputting into the repo-level `app/` folder (which the backend serves)

## Run (manual)

From the repo root:

1) Backend:

```powershell
${PWD}\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 7080 --reload --app-dir "${PWD}\backend\orchestrator"
```

2) Frontend watcher (no server):

```powershell
npm --prefix frontend run build:vite:watch
```

## Notes

- `npm run dev` is disabled on purpose to keep payment/subscription off the Vite server.
