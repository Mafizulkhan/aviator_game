"""
Anti-Gravity Backend — In-Memory Sliding-Window Rate Limiter (Sprint 6)
Protects security-sensitive endpoints (login, register, cash-out, ws, fairness)
against abuse, brute force, and denial of service.
"""

from __future__ import annotations

import time
from collections import defaultdict
from typing import Callable, Dict, List

from fastapi import HTTPException, Request, WebSocket, status

from backend.config import settings


class RateLimiter:
    """Thread-safe sliding-window rate limiter."""

    _store: Dict[str, List[float]] = defaultdict(list)

    @classmethod
    def is_allowed(
        cls,
        key: str,
        max_requests: int,
        window_seconds: float = 60.0,
    ) -> bool:
        """
        Check if a request under `key` is allowed under the rate limit.
        Removes timestamps older than (now - window_seconds).
        Returns True if allowed (and logs the timestamp), False if exceeded.
        """
        if not settings.RATE_LIMIT_ENABLED:
            return True

        now = time.monotonic()
        cutoff = now - window_seconds
        records = cls._store[key]

        # Prune old timestamps
        cls._store[key] = [t for t in records if t > cutoff]

        if len(cls._store[key]) >= max_requests:
            return False

        cls._store[key].append(now)
        return True

    @classmethod
    def check_http_rate_limit(
        cls,
        request: Request,
        action: str,
        max_requests: int,
        window_seconds: float = 60.0,
    ) -> None:
        """
        Enforce rate limiting on an HTTP request by client IP + action.
        Raises HTTP 429 Too Many Requests if rate limit is exceeded.
        """
        if not settings.RATE_LIMIT_ENABLED:
            return

        client_ip = request.client.host if request.client else "127.0.0.1"
        key = f"http:{action}:{client_ip}"

        if not cls.is_allowed(key, max_requests, window_seconds):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Too many requests for {action}. Please try again later.",
                headers={"Retry-After": str(int(window_seconds))},
            )

    @classmethod
    def check_ws_rate_limit(
        cls,
        client_ip: str,
        action: str,
        max_requests: int,
        window_seconds: float = 60.0,
    ) -> bool:
        """
        Check rate limiting for WebSocket connections or incoming messages.
        Returns True if allowed, False if exceeded.
        """
        if not settings.RATE_LIMIT_ENABLED:
            return True

        key = f"ws:{action}:{client_ip}"
        return cls.is_allowed(key, max_requests, window_seconds)

    @classmethod
    def clear(cls) -> None:
        """Reset all rate limit tracking."""
        cls._store.clear()


def rate_limited(action: str, max_requests: int, window_seconds: float = 60.0) -> Callable:
    """FastAPI dependency for applying rate limits to endpoints."""
    async def _rate_limit_dependency(request: Request) -> None:
        RateLimiter.check_http_rate_limit(request, action, max_requests, window_seconds)
    return _rate_limit_dependency
