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
- `CORS_ALLOW_ORIGINS` (optional)
- `CORS_ALLOW_ORIGIN_REGEX` (optional)
- `CORS_ALLOW_CREDENTIALS` (`true/false`)
- `ENTERPRISE_EMAILS` (optional)
- `TRIAL_ENABLED` (`true/false`)
- `TRIAL_DAYS` (number)
- `USAGE_LIMITS_ENABLED` (`true/false`)
- `RATE_LIMIT_ENABLED` (`true/false`)

Stripe (only if billing is enabled):
- `STRIPE_SECRET_KEY`
- `STRIPE_WEBHOOK_SECRET`
- `STRIPE_PRICE_STUDENT*`, `STRIPE_PRICE_PRO*` (as used by your billing route)

## 3) Networking / TLS

- Confirm the public domain points to the host.
- Confirm HTTPS is on (recommended) and HTTP redirects to HTTPS.

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
