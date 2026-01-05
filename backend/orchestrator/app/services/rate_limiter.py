from __future__ import annotations

import os
import threading
import time
from collections import deque
from dataclasses import dataclass
from typing import Deque, Dict, Tuple


def rate_limits_enabled() -> bool:
    return os.getenv("RATE_LIMIT_ENABLED", "true").strip().lower() in {"1", "true", "yes"}


def _limit_for_action(action: str) -> int:
    # Per-minute limits, simple and safe defaults.
    action = (action or "").strip().lower()
    if action == "plan":
        raw = os.getenv("RATE_LIMIT_PLAN_PER_MINUTE", "10")
    elif action == "chat":
        raw = os.getenv("RATE_LIMIT_CHAT_PER_MINUTE", "60")
    elif action == "patch":
        raw = os.getenv("RATE_LIMIT_PATCH_PER_MINUTE", "6")
    else:
        raw = os.getenv("RATE_LIMIT_DEFAULT_PER_MINUTE", "0")
    try:
        return max(0, int(str(raw).strip()))
    except Exception:
        return 0


@dataclass(frozen=True)
class RateLimitResult:
    allowed: bool
    limit: int
    remaining: int
    retry_after_seconds: int


class _RateLimiter:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        # key: (actor, action) -> timestamps (seconds)
        self._hits: Dict[Tuple[str, str], Deque[float]] = {}

    def check(self, *, actor: str, action: str, window_seconds: int = 60) -> RateLimitResult:
        limit = _limit_for_action(action)
        if limit <= 0:
            return RateLimitResult(allowed=True, limit=0, remaining=0, retry_after_seconds=0)

        now = time.time()
        key = (actor, action)

        with self._lock:
            q = self._hits.get(key)
            if q is None:
                q = deque()
                self._hits[key] = q

            cutoff = now - float(window_seconds)
            while q and q[0] <= cutoff:
                q.popleft()

            if len(q) >= limit:
                oldest = q[0] if q else now
                retry_after = int(max(1.0, (oldest + float(window_seconds)) - now))
                return RateLimitResult(
                    allowed=False,
                    limit=limit,
                    remaining=0,
                    retry_after_seconds=retry_after,
                )

            q.append(now)
            remaining = max(0, limit - len(q))
            return RateLimitResult(
                allowed=True,
                limit=limit,
                remaining=remaining,
                retry_after_seconds=0,
            )


_limiter = _RateLimiter()


def check_rate_limit(*, actor: str, action: str) -> RateLimitResult:
    return _limiter.check(actor=actor, action=action)
