from __future__ import annotations

from fastapi import Request

from app.services.auth import try_get_user
from app.services.request_ip import get_request_client_ip


def get_project_owner_key(request: Request) -> str:
    """Owner key used to scope projects per visitor.

    - Authenticated users: user:<user_id>
    - Anonymous visitors: anon:<client_ip>

    This mirrors the actor logic in the usage middleware.
    """

    user = try_get_user(request)
    if user and user.id:
        return f"user:{user.id}"

    host = get_request_client_ip(request)
    return f"anon:{host}"
