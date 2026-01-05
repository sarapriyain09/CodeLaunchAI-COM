from __future__ import annotations

import os
from fastapi import Request


def _trust_proxy_headers() -> bool:
    # Render / most PaaS setups terminate TLS at a proxy and pass the real IP
    # via X-Forwarded-For. Trusting these headers can be spoofed in direct-to-app
    # deployments, so keep it configurable.
    raw = os.getenv("TRUST_PROXY_HEADERS", "")
    if raw.strip():
        return raw.strip().lower() in {"1", "true", "yes"}

    # Default: trust in Render-like environments, otherwise still trust (safe-ish)
    # because worst-case impact is only per-IP metering.
    return True


def get_request_client_ip(request: Request) -> str:
    if _trust_proxy_headers():
        xff = (request.headers.get("x-forwarded-for") or "").strip()
        if xff:
            # X-Forwarded-For: client, proxy1, proxy2
            first = xff.split(",", 1)[0].strip()
            if first:
                return first

        xri = (request.headers.get("x-real-ip") or "").strip()
        if xri:
            return xri

        fwd = (request.headers.get("forwarded") or "").strip()
        if fwd:
            # Forwarded: for=1.2.3.4;proto=https;by=...
            parts = [p.strip() for p in fwd.split(";")]
            for part in parts:
                if part.lower().startswith("for="):
                    value = part.split("=", 1)[1].strip().strip('"')
                    # May be like: for=1.2.3.4 or for="[2001:db8::1]"
                    if value.startswith("[") and "]" in value:
                        return value[1 : value.index("]")]
                    # Strip optional port
                    if ":" in value and value.count(":") == 1:
                        host = value.split(":", 1)[0].strip()
                        if host:
                            return host
                    if value:
                        return value

    host = (request.client.host if request.client else "unknown")
    return host or "unknown"
