cd D:\Five_Pillar\07Software\SplendidTechnology\codelaunchcom
backend\orchestrator\.venv\Scripts\python -m uvicorn app.main:app --app-dir backend\orchestrator --reload --port 7080# CodeLaunchAI — Lovable.dev Inspired Builder

This document captures the launch plan for rebuilding CodeLaunchAI as a Lovable.dev style experience: chat with AI, generate a blueprint, see a live preview, and deploy/export.

---

## Product Pillars

1. **Chat UX**: Conversational intake, follow-up questions, and iteration history.
2. **Planner / Blueprint Engine**: Convert intent → structured JSON (pages, sections, data models, integrations).
3. **Preview Runtime**: Render the generated experience instantly; allow inline edits.
4. **Deploy & Export**: ZIP export, GitHub sync, and later custom domains.

---

## MVP Scope (4–6 weeks solo)

| Track | Deliverables |
| --- | --- |
| Landing & Auth | Marketing home, email/password login, user profile. |
| Project Workspace | Split view: chat (left) + preview (right); tabs for Files / Preview / Deploy. |
| Generator Pipeline | Step A: chat → blueprint JSON. Step B: blueprint → file tree (Next.js + Tailwind). Step C: run preview sandbox. |
| Deploy (MVP) | ZIP export; optional GitHub push. |

Phase 2 niceties: template gallery, managed backend (DB/auth/storage), collaboration controls.

---

## High-Level Architecture

### Frontend
- Next.js + TypeScript + Tailwind.
- Workspace page with chat panel, Monaco editor, and Sandpack/WebContainer preview iframe.
- Auth (Supabase or custom) and project dashboard.

### Backend Services
1. **GPT Gateway (FastAPI)** — already started; handles `/chat`.
2. **Orchestrator API (FastAPI)** — `/projects`, `/blueprint`, `/generate`, `/deploy`.
3. **Generator Worker** — runs LLM prompts to create structured plans + files.
4. **Preview Runtime** — start with in-browser bundler; upgrade to server containers later.

### Storage
- Postgres (Supabase) for users/projects/messages.
- Object storage (S3/Supabase) for generated artifacts.

---

## Blueprint-First Flow

1. **Blueprint Schema** — Strict JSON schema with sections: `appType`, `routes`, `components`, `dataModels`, `integrations`, `styleTokens`.
2. **Generation** — Templates + scoped prompts to fill each file; validate via TypeScript build + ESLint.

---

## APIs to Implement

| Endpoint | Purpose |
| --- | --- |
| `POST /projects` | Create project; seed system/user prompts. |
| `POST /projects/{id}/chat` | Persist chat, call GPT, return assistant reply. |
| `POST /projects/{id}/blueprint` | Produce structured plan. |
| `POST /projects/{id}/generate` | Return array of `{ path, content }` files. |
| `POST /projects/{id}/deploy` | Trigger ZIP/GitHub export. |

---

## Preview Strategy

- **MVP**: Sandpack/WebContainer to run generated React app client-side.
- **Later**: Containerized preview workers for full-stack apps.

---

## Monetization Notes

- Credits + subscription tiers (mirror Lovable): free daily credits, Pro monthly, Business for teams/SSO.

---

## Immediate Next Steps

1. Decide preview implementation (Sandpack vs server containers).
2. Define Blueprint JSON schema + Pydantic models.
3. Add `/blueprint` and `/generate` endpoints atop FastAPI stack.
4. Scaffold Next.js workspace UI with chat + files + preview.

Once these are in place, we can iterate toward Lovable-level polish (templates, collaboration, managed backend, etc.).

---

## 8-Week Build Plan — CodeLaunchAI (Lovable Style)

### Week 1 — Foundation & Project Setup
- Backend: finalize repo layout (`backend/gpt-chat`, `backend/orchestrator`), env config, CORS, logging, `/health`.
- Frontend: scaffold React app, routing for login/dashboard/workspace, base layout (sidebar + main panel).
- ✅ Deliverable: backend + frontend run reliably, `/health` responds, workspace shell renders.

### Week 2 — Auth, Projects & State
- Backend: user model, project model, CRUD endpoints (`POST /projects`, `GET /projects`, `GET /projects/{id}`).
- Frontend: email/password auth UI, project list, create project modal + navigation into workspace.
- ✅ Deliverable: authenticated user can manage multiple projects and enter workspace context.

### Week 3 — Chat & Blueprint Planning
- Backend: persist chat messages, harden `/plan` (retry invalid JSON), store blueprint per project.
- Frontend: chat UI with typing indicator, blueprint viewer tab for generated JSON.
- ✅ Deliverable: chat idea → saved blueprint, user can inspect structured plan.

### Week 4 — Code Generation
- Backend: refine `/generate`, ensure deterministic Vite+React templates, store file tree artifacts.
- Frontend: "Generate App" CTA, file tree browser, read-only code viewer (Monaco).
- ✅ Deliverable: blueprint → tangible files users can inspect.

### Week 5 — Preview & Streaming Build Logs
- Backend: `/materialize`, `/build`, `/preview/{id}`, `/projects/{id}/build/stream` SSE logs.
- Frontend: preview iframe, live log panel, auto-refresh preview on build success.
- ✅ Deliverable: Lovable-style moment — click generate, watch logs, see live app.

### Week 6 — Iteration & Patch Updates
- Backend: `/patch` endpoint to update blueprint + regenerate touched files, incremental rebuild if possible.
- Frontend: "Update app" chat flow, diff indicators, faster rebuild feedback.
- ✅ Deliverable: iterative edits work without wiping project.

### Week 7 — Export, Pricing & Limits
- Backend: ZIP export, credit usage tracking, basic rate limits.
- Frontend: download button, usage meter, upgrade CTA (placeholder or Stripe test mode).
- ✅ Deliverable: users can export code and understand limits/upsell.

### Week 8 — Polish, SEO & Launch Prep
- Product: landing page with SEO copy, value prop, examples gallery.
- Engineering: error states, empty states, performance sweeps, safety guardrails.
- Ops: deploy backend/frontend, domain + HTTPS, monitoring basics.
- ✅ Deliverable: public MVP ready for early adopters.

### Core Principles
- Blueprint-first flow, avoid full regeneration unless necessary.
- Preview before perfection; ship value quickly.
- Export builds trust; prioritize speed over secondary features.

### Post-MVP Ideas
- Next.js generator, e-commerce templates, team collaboration, template marketplace, AI tutor mode.
