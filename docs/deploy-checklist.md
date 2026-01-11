# Deploy Checklist (Week 9 / Option A)

Use this to do a real-host “stabilize & ship” pass.

## 1) Build artifacts

- Frontend build output should exist in `/app/` at repo root (served by backend at `/app/`).
- Confirm backend serves `/app/` as static files.

## 2) Environment variables

Backend (FastAPI orchestrator):
- `OPENAI_API_KEY` (optional; enables real OpenAI calls)
- `DATABASE_URL` (optional; enables Postgres persistence)
- `DB_DISABLE` (`true/false`)
- `DB_INIT_ON_STARTUP` (`true/false`)
- `PUBLIC_APP_ORIGIN` (recommended) — set to `https://www.codlearn.com` so any direct backend-hosted preview URLs can 302-redirect back to the public domain.
- `CORS_ALLOW_ORIGINS` (optional)
- `CORS_ALLOW_ORIGIN_REGEX` (optional)
- `CORS_ALLOW_CREDENTIALS` (`true/false`)
- `ENTERPRISE_EMAILS` (optional)
- `TRIAL_ENABLED` (`true/false`)
- `TRIAL_DAYS` (number)
- `USAGE_LIMITS_ENABLED` (`true/false`)
- `RATE_LIMIT_ENABLED` (`true/false`)

Frontend (Vite build-time env):
- `VITE_ORCH_BASE_URL` (required for split hosting) — set to the backend URL (e.g. `https://api.codlearn.com`).
- `VITE_PUBLIC_SITE_URL` (optional) — set to the public site URL (e.g. `https://www.codlearn.com`) for building absolute links.

Note: Vite injects `VITE_*` vars at build time. If `VITE_ORCH_BASE_URL` is missing or wrong, the deployed JS can end up calling `http://localhost:7080` / `http://127.0.0.1:7080` and you’ll see `ERR_CONNECTION_REFUSED` in the browser.

Stripe (only if billing is enabled):
- `STRIPE_SECRET_KEY`
- `STRIPE_WEBHOOK_SECRET`
- `STRIPE_PRICE_STUDENT*`, `STRIPE_PRICE_PRO*` (as used by your billing route)

## 3) Networking / TLS

- Confirm the public domain points to the host.
- Confirm HTTPS is on (recommended) and HTTP redirects to HTTPS.

If frontend (Vercel) and backend (Render) are split:
- Proxy preview routes through the public domain to avoid browser warnings about the Render hostname.
- Add a Vercel rewrite for `/preview/*` (and `/assets/*` for older builds) to point to the backend.
- This repo includes `vercel.json` with these rewrites (update the destination host if your Render URL changes).

## 4) Minimal monitoring

- Add an uptime check against `GET /health`.
- Confirm logs are captured (stdout is fine for MVP).

## 5) Run smoke test

Run the included PowerShell script against the deployed host:

```powershell
# If backend + frontend are on the same domain:
powershell -ExecutionPolicy Bypass -File scripts\\smoke_test.ps1 -BackendUrl https://YOUR_DOMAIN

# If backend and frontend are split (e.g., backend on Render, frontend on www domain):
powershell -ExecutionPolicy Bypass -File scripts\\smoke_test.ps1 \
	-BackendUrl https://YOUR_BACKEND \
	-FrontendUrl https://YOUR_FRONTEND
```

If this returns exit code 0, the core flows are up.

## 6) Manual sanity (5 minutes)

- Load `/` and ensure it redirects to `/app/`.
- Open `/app/` and navigate to the builder.
- Click Generate once; ensure build progress moves and preview eventually opens.
