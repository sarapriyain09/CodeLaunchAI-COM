# Codlearn Weekly Task Board

A practical, solo-friendly task board derived from the 8-week roadmap. Track status with the checkbox next to each item.

---

## Week 1 — Foundation & Project Setup
- [x] Backend: orchestrator skeleton + `/health`
- [x] Backend: CORS baseline
- [x] Ops/Dev hardening: DB startup retry + fail-open (clear errors, optional continue without DB)
- [x] Frontend: workspace UI scaffolding
- [x] Frontend: Tailwind/Vite setup stabilized
- [x] Deliverable check: backend + frontend run reliably and `/health` responds

Notes:
- We are not using a separate `backend/gpt-chat` service right now. The orchestrator can call OpenAI directly via `OPENAI_API_KEY`.

## Week 2 — Auth, Projects & State
- [x] Frontend: per-session project id (no more hardcoded `demo1`)
- [x] Backend: implement project model + endpoints (`POST/GET /projects`, `GET /projects/{id}`)
- [x] Frontend: project list + create project flow
- [x] Deliverable check: user can create/open multiple projects

## Week 3 — Chat & Blueprint Planning
- [x] Backend: `/plan` retry invalid JSON + offline fallback blueprint
- [x] Backend: connect `/plan` to OpenAI (set `OPENAI_API_KEY`, choose model)
- [x] Backend: `/chat` endpoint for clarifying questions
- [x] Backend: persist chat history per project
- [x] Frontend: blueprint viewer tab (read-only JSON)
- [x] Deliverable check: idea → blueprint visible in UI

## Week 4 — Code Generation
- [x] Backend: `/generate` deterministic Vite+React templates
- [x] Frontend: "Generate" triggers plan → generate → materialize → build stream
- [x] Frontend: file tree browser + read-only code viewer (Monaco)
- [x] Backend: store generated file tree per project (persistence)
- [x] Deliverable check: blueprint → tangible files rendered in UI

## Week 5 — Preview & Streaming Build Logs
- [x] Backend: `/materialize`, `/build`, `/preview/{id}`, `/projects/{id}/build/stream`
- [x] Backend: SSE logs emit install/build progress + preview URL
- [x] Frontend: preview iframe wired to backend
- [x] Frontend: live log panel + auto-refresh on build success
- [x] Deliverable check: user clicks generate, watches logs, sees app in iframe

## Week 6 — Iteration & Patch Updates
- [x] Backend: `/patch` endpoint (update blueprint + regenerate + apply changed files)
- [x] Backend: incremental rebuild path when only a few files change (build stream with `install=false`)
- [x] Backend: no-Postgres dev mode persistence for state/files/patch (JSON on disk)
- [x] Frontend: "Update" flow + changed/removed counts + rebuild preview
- [x] Deliverable check: iterative edits work without wiping project

## Week 7 — Export, Pricing & Limits
- [x] Backend: ZIP export endpoint (subscription gated)
- [x] Backend: AI credits/month tracking + enforcement + free trial tier
- [x] Backend: basic rate limits (plan/chat/patch)
- [x] Frontend: usage meter + upgrade CTA (Pricing redirect + subscribe flow)
- [x] Deliverable check: users can export code and understand usage limits

## Week 8 — Polish, SEO & Launch Prep
- [x] Product: landing page copy refresh (value prop + pricing alignment)
- [x] Product: examples gallery (minimal static cards)
- [x] Engineering: empty states (no project/files/preview yet)
- [x] Engineering: friendly error states (402 credits / 429 rate limit / OpenAI offline)
- [x] Engineering: build progress indicator (0–100% while preview builds)
- [x] Engineering: show generated code to user (file list + file contents)
- [x] Engineering: performance sweep (reduce polling/churn, keep idle quiet)
- [x] Ops: deploy backend + built frontend artifacts served at `/app/`
- [x] Ops: env var checklist documented (DB/no-DB, OpenAI, Stripe optional)
- [x] Ops: monitoring basics (uptime on `/health`, readable logs)
- [x] Deliverable check: smoke test end-to-end flows (plan/generate/patch/export/limits)

Week 8 status (Jan 4, 2026):
- Landing now includes Examples section and updated pricing/trial copy.
- Public home `/` now redirects to `/app/` (no legacy/corrupt root HTML).
- Builder UX: friendly 402/429 messaging + OpenAI-offline indicator.
- Builder UX: clear no-preview-yet messaging + build progress (0–100%).
- Builder UX: generated code is shown in-app (file picker + contents).
- Smoke tests: `/health`, `/`→`/app/` redirect, `/app/` serving, `/chat`, `/plan`, plan→generate, and materialize→build→preview verified locally. Patch/export/limits depend on credits/auth; 402/429 paths are handled in UI.

---

## Core Principles Checklist
- [ ] Always generate/update blueprint before touching files
- [ ] Avoid full regenerations unless necessary
- [ ] Prioritize preview speed over feature breadth
- [ ] Ensure export stays frictionless (ZIP or GitHub)
