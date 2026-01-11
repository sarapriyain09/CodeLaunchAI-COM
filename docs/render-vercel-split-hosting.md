# Render + Vercel split hosting (www frontend + Render backend)

This project is deployed as:

- **Frontend**: Vercel (public domain like `https://www.codlearn.com`)
- **Backend**: Render (FastAPI orchestrator)
- **Goal**: the browser calls the backend via **same-origin proxy** at `https://www.codlearn.com/api/*` to avoid CORS.

## Architecture (recommended)

### 1) Create a stable API hostname (best practice)

To avoid future breakages when the Render service URL changes, use a stable DNS name:

- `api.codlearn.com` (or `api.<your-domain>`)

Then Vercel rewrites always point to `https://api.codlearn.com`, and when you migrate or recreate the Render service you only update **DNS** (or Render custom domain target), not frontend code.

### 2) Vercel proxies `/api/*` to the backend

Vercel is configured to rewrite requests:

- `GET https://www.codlearn.com/api/health` → `GET https://<backend-host>/health`
- `POST https://www.codlearn.com/api/projects/...` → `POST https://<backend-host>/projects/...`

This proxy eliminates browser CORS issues.

### 3) Frontend chooses `/api` in production

The frontend client in `frontend/src/api/orchestrator.ts` defaults to:

- Local: same origin (e.g. `http://127.0.0.1:7080`)
- Production: `${window.location.origin}/api`

So in production, the JS will call `https://www.codlearn.com/api/...` (which Vercel rewrites to the backend).

## Render setup

1) Deploy the FastAPI backend on Render.
2) Confirm health endpoint works:

- `GET /health` returns `200`

3) (Recommended) Add a **custom domain** in Render:

- Add `api.codlearn.com` to the Render service (Render dashboard → Settings → Custom Domains)
- Render will show the DNS record(s) you must create.

4) DNS records (in your DNS provider):

- Create `CNAME api -> <render-provided target>` (preferred)
- Or follow the exact A/CNAME record Render provides.

5) Backend env vars (Render):

- `PUBLIC_APP_ORIGIN=https://www.codlearn.com`
- `CORS_ALLOW_ORIGINS=https://www.codlearn.com,https://codlearn.com` (only needed if you ever bypass the proxy and call Render directly)

## Vercel setup

### 1) Rewrites / proxy configuration

This repo uses Vercel rewrites in either `vercel.json` (repo root) and/or `frontend/vercel.json` (if Vercel project root is `frontend/`).

The rewrites must point to the backend host:

- Preferred stable host: `https://api.codlearn.com`
- Temporary host (works but fragile): your Render default URL like `https://<service>.onrender.com`

Quick sanity endpoints:

- `GET /__rewrite_test` should proxy to backend `/health` and return `200`
- `GET /api/health` should return `200`

### 2) Which `vercel.json` is used?

- If your Vercel project root is the repo root (`./`), Vercel reads `vercel.json`.
- If your Vercel project root is `frontend/`, Vercel reads `frontend/vercel.json`.

Keep these in sync, or delete the unused one to avoid confusion.

### 3) Frontend build-time environment variables

If you are using the Vercel proxy (`/api`) you typically **do not need** to set a backend URL in the frontend build.

- Recommended (proxy mode):
  - Don’t set `VITE_ORCH_BASE_URL` (or set it to `/api` / same-origin)

Only set `VITE_ORCH_BASE_URL` to a full backend URL if you intend the browser to call the backend directly (CORS must be configured on Render):

- `VITE_ORCH_BASE_URL=https://api.codlearn.com`

## How to change the backend in the future (no downtime)

### Best practice (stable `api.` domain)

1) Update Render service (or replace it).
2) Point `api.codlearn.com` to the new backend (Render custom domain + DNS).
3) No Vercel changes needed.

### If you are using the Render default URL (fragile)

1) Update the destination host in Vercel rewrites (`vercel.json` / `frontend/vercel.json`).
2) Commit + push.
3) Trigger a Vercel redeploy.

## Troubleshooting

### Symptom: `HTTP 502` + `DNS_HOSTNAME_NOT_FOUND`

Cause: Vercel is rewriting to a hostname that doesn’t exist in DNS.

Fix:

- Confirm the rewrite destination hostname resolves in DNS.
- Confirm backend is reachable at `/health`.
- Confirm Vercel is deployed with the latest `vercel.json`.

Quick checks:

- `https://www.codlearn.com/__rewrite_test`
- `https://www.codlearn.com/api/health`
- `https://api.codlearn.com/health` (if you use the stable `api.` domain)
