# CodeLaunchAI — Lovable.dev Inspired Builder

## Local run (backend-only mode)

From the repo root:

```powershell
cd D:\Five_Pillar\07Software\SplendidTechnology\codelaunchcom
backend\orchestrator\.venv\Scripts\python -m uvicorn app.main:app --app-dir backend\orchestrator --reload --port 7080
```

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

---

## Week 8 Execution Plan (Jan 4–Jan 10, 2026)

### Status update (Jan 4, 2026)

Done:
- Landing: pricing alignment + “Examples” gallery section.
- Public home route: `/` now cleanly redirects to `/app/`.
- Builder UX: friendlier handling for HTTP 402 (credits/subscription) and 429 (rate limiting).
- Builder UX: OpenAI-offline indicator + preview/file empty states.
- Builder UX: build progress indicator (0–100%) while preview builds.
- Builder UX: show generated code to user (file picker + file contents).
- Smoke test (local): `/health`, `/` redirect, `/app/` serving, `/chat`, `/plan`, plan→generate, and materialize→build→preview.

Remaining (Week 8):
- Fill remaining empty/error states (no files/preview yet + offline OpenAI messaging).
- Performance sweep + idle quieting.
- Ops docs: env var checklist + monitoring basics.
- Full smoke test pass.

Goal: ship a stable, public-facing MVP (landing + app) with good first-run UX, clear upgrade path, and basic operational readiness.

Non-goals (Week 8): new core features (no new generators, no new UI pages, no new billing flows beyond what exists).

### Ops Checklist (Week 8)

#### Environment variables

Backend (FastAPI orchestrator):
- `OPENAI_API_KEY` (optional) — enables real OpenAI calls; without it the app should use offline fallbacks where implemented.
- `DATABASE_URL` (optional) — enables Postgres persistence.
- `DB_DISABLE` (optional, `true/false`) — forces DB off (useful for dev / no-DB mode).
- `DB_INIT_ON_STARTUP` (optional, `true/false`) — controls DB init on startup.
- `CORS_ALLOW_ORIGINS` (optional) — comma-separated origins; defaults to `*`.
- `CORS_ALLOW_CREDENTIALS` (optional, `true/false`) — defaults to `false`.
- `ENTERPRISE_EMAILS` (optional) — comma-separated allowlist for enterprise tier.
- `TRIAL_ENABLED` (optional, `true/false`) — defaults to `true`.
- `TRIAL_DAYS` (optional) — defaults to `14`.

Stripe (optional; required only if billing flows are enabled):
- `STRIPE_SECRET_KEY`
- `STRIPE_WEBHOOK_SECRET`
- `STRIPE_PRICE_STUDENT`
- `STRIPE_PRICE_PRO`
- `STRIPE_PRICE_ID_MONTHLY`
- `STRIPE_PRICE_ID_YEARLY`

Frontend (Vite):
- `VITE_ORCH_BASE_URL` (optional) — overrides API base URL; defaults to `window.location.origin`.

#### Monitoring basics
- Uptime check: `GET /health` should return `{ "ok": true }`.
- Logs: keep backend logs readable (rate limits, build stream failures, export failures, and OpenAI connectivity errors should be visible).
- Smoke-test on deploy: verify `/` redirects to `/app/` and `/app/` loads.

#### Smoke test checklist (end-to-end)
- Flow A: open `/` → verify redirect to `/app/` and landing loads.
- Flow B: open builder `/app/#/builder` → send chat message → assistant reply appears.
- Flow C: click Generate → build progress increments → Preview ready → Open preview works.
- Flow D: click Update after a change instruction → rebuild works.
- Flow E: export ZIP (when auth/subscription rules apply) → correct messaging for 401/402.
- Flow F: spam chat/plan/patch endpoints → verify 429 UI message includes retry hint when available.

Quick-run:
- See docs/deploy-checklist.md
- Run scripts/smoke_test.ps1 against the deployed BackendUrl (and FrontendUrl if split)

### Deliverables (measurable)

1) Public landing is clear + trustworthy
- Value prop is crisp, pricing tiers match product limits, and users can find `Subscribe` and `App` quickly.
- At least 1–3 concrete “example” entries (can be simple cards) showing what the builder can produce.

2) App UX is resilient
- Empty states: no-project, no-files, no-preview yet.
- Error states: common backend errors are human-readable (offline OpenAI, credits exceeded, rate limited).

3) Ops readiness
- Deployment steps are documented.
- Health endpoint works, basic logs are readable, and core flows are smoke-tested.

### Day-by-day plan

Day 1 (Jan 4) — Landing + messaging
- Update landing copy + pricing section to reflect current tiers (Trial/Student/Pro/Enterprise).
- Add an “Examples” gallery section (minimal: static cards with title + bullets).
- Acceptance: `http://127.0.0.1:7080/` reads well on desktop and mobile widths.

Day 2 (Jan 5) — App empty/error states
- Workspace: ensure safe rendering when project/files/preview are missing.
- Show friendly messages for `402` (credits exceeded) and `429` (rate limited) without console spew.
- Acceptance: builder never hard-crashes on common failures.

Day 3 (Jan 6) — Performance + guardrails
- Reduce accidental re-fetch/poll churn; keep status polling reasonable.
- Ensure build log stream UI handles disconnect/reconnect gracefully.
- Acceptance: CPU/network stays sane when idle in builder.

Day 4 (Jan 7) — Deploy backend + frontend artifacts
- Confirm build pipeline (frontend `vite build --watch` → repo `app/` served by backend).
- Document deployment env vars and “no-DB mode” fallback expectations.
- Acceptance: a fresh deploy can load `/`, `/subscribe.html`, and `/app/`.

Day 5 (Jan 8) — Monitoring basics
- Decide minimal monitoring: request logs + uptime check on `/health`.
- Add any missing structured log lines for build/export/usage-limit failures.
- Acceptance: operational signals exist to debug user reports.

Day 6 (Jan 9) — Full smoke test pass
- Flow 1: new visitor → subscribe page → app opens.
- Flow 2: plan → generate → preview appears.
- Flow 3: patch → preview updates.
- Flow 4: credits exceeded → upgrade CTA works.
- Flow 5: spam `POST /chat` → `429` shows friendly message.

Day 7 (Jan 10) — Buffer + launch checklist
- Fix highest-impact issues found in smoke test.
- Write “known limitations” list.
- Acceptance: ready to share with early adopters.

### Core Principles
- Blueprint-first flow, avoid full regeneration unless necessary.
- Preview before perfection; ship value quickly.
- Export builds trust; prioritize speed over secondary features.

### Post-MVP Ideas
- Next.js generator, e-commerce templates, team collaboration, template marketplace, AI tutor mode.
