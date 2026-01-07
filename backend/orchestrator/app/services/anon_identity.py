from __future__ import annotations

import re
import uuid

from fastapi import Request


COOKIE_NAME = "cla_anon_id"
_ID_RE = re.compile(r"^[a-f0-9]{32}$", re.IGNORECASE)


def get_or_create_anon_id(request: Request) -> tuple[str, bool]:
    """Return a stable anonymous id for this browser via cookie.

    This prevents shared-IP environments (schools, offices, NAT, VPN) from sharing a
    single usage bucket.

    Returns (anon_id, is_new).
    """

    raw = (request.cookies.get(COOKIE_NAME) or "").strip()
    if raw and _ID_RE.match(raw):
        return raw.lower(), False

    return uuid.uuid4().hex, True
