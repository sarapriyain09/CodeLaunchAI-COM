# CodeLaunchAI-COM

Monorepo for Codlearn/CodeLaunchAI web app, including:
- Marketing and app pages (root and app/ static output)
- Frontend source project (Vite + TypeScript + Tailwind)
- Backend orchestrator API (FastAPI)
- Deployment and operations docs

## What This Web App Does

CodeLaunchAI helps users build web apps with AI from idea to preview.

- Converts a plain-English idea into a structured app blueprint (`/plan`)
- Generates a React + TypeScript + Tailwind project from that blueprint (`/generate`)
- Lets users chat with an AI assistant to refine requirements (`/chat`)
- Applies iterative updates to existing projects using natural-language instructions (`/projects/{id}/patch`)
- Materializes, builds, and serves project previews (`/projects/{id}/materialize`, `/projects/{id}/build`, `/previews/{id}`)
- Includes authentication, subscription billing, usage tracking, and rate limiting for production readiness

## Software Used (Including AI)

### Frontend

- Vite
- TypeScript
- Tailwind CSS
- ESLint

### Backend

- Python
- FastAPI
- Uvicorn
- Pydantic
- HTTPX
- SQLAlchemy + PostgreSQL (psycopg)

### AI and Generation

- OpenAI Chat Completions API for planning, chat, and code-content generation
- Default LLM model via env: `OPENAI_MODEL` (current default in code: `gpt-4o-mini`)
- Optional fallback gateway (`GPT_CHAT_BASE_URL`) when direct OpenAI key is not set
- Optional OpenAI Images API flow to replace placeholder images with generated PNG assets

### Product Integrations

- Stripe for subscriptions and webhook-based billing lifecycle updates
- JWT-based authentication with email/password and Google auth support

## Repository Structure

- `app/` - Built frontend assets and static app pages served in production
- `frontend/` - Frontend source code and build tooling
- `backend/orchestrator/` - FastAPI orchestrator service
- `docs/` - Deployment plans and operational checklists
- `scripts/` - Smoke tests and verification helpers
- `blog/` - Blog HTML pages (root-level static copy)

## Local Development

### 1) Frontend build pipeline

From repository root:

```powershell
npm --prefix frontend install
npm --prefix frontend run build
```

Notes:
- The `frontend` package disables standard Vite `dev` mode.
- For backend-only workflow with watched frontend output:

```powershell
npm --prefix frontend run build:vite:watch
```

### 2) Backend orchestrator

From repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend/orchestrator/requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 7080 --app-dir backend/orchestrator
```

### 3) Open app

- App shell: `http://127.0.0.1:7080/app/`
- Health check: `http://127.0.0.1:7080/health`

## Environment Variables

Common backend variables include:
- `OPENAI_API_KEY`
- `DATABASE_URL`
- `PUBLIC_APP_ORIGIN`
- `CORS_ALLOW_ORIGINS`
- `TRIAL_ENABLED`
- `TRIAL_DAYS`

Frontend (build-time):
- `VITE_ORCH_BASE_URL`
- `VITE_PUBLIC_SITE_URL`

See `docs/deploy-checklist.md` for full environment guidance.

## Deployment Notes

- Root `vercel.json` is used for frontend/static hosting behavior.
- Split hosting setup (e.g., Vercel + Render) is documented in:
  - `docs/render-vercel-split-hosting.md`
- Pre-release checklist:
  - `docs/deploy-checklist.md`

## Smoke Testing

Run the included PowerShell smoke test:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\smoke_test.ps1 -BackendUrl https://YOUR_BACKEND
```

If frontend and backend are split, pass both `-BackendUrl` and `-FrontendUrl`.
