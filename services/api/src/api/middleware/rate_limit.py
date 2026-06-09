"""Sliding-window rate limiter implemented as ASGI middleware.

Uses an in-memory counter per (user_id | client_ip) with a 60-second window.
In production, counters would live in Redis for cross-replica consistency;
the algorithm is identical — only the storage backend changes.

Configuration (from Settings):
  rate_limit_per_minute  — normal endpoints
  rate_limit_burst_per_minute — expensive endpoints tagged with X-Rate-Limit-Tier: burst

A 429 response includes Retry-After and X-RateLimit-* headers.
"""

from __future__ import annotations

import time
from collections import defaultdict, deque

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp


class SlidingWindowRateLimiter(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp, requests_per_minute: int, burst_per_minute: int) -> None:
        super().__init__(app)
        self._rpm = requests_per_minute
        self._burst_rpm = burst_per_minute
        # key → deque of request timestamps (monotonic seconds)
        self._windows: dict[str, deque[float]] = defaultdict(deque)

    def _identity(self, request: Request) -> str:
        """Extract the rate-limit identity: authenticated user_id or client IP."""
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            # Use sub claim if decodable; fall back to raw token hash
            import hashlib

            token = auth[7:]
            # Decode without verification just to get the sub for bucketing.
            # We do NOT use this as auth — real validation is in the dep.
            import base64
            import json

            try:
                parts = token.split(".")
                padded = parts[1] + "=" * (-len(parts[1]) % 4)
                claims = json.loads(base64.b64decode(padded))
                sub = claims.get("sub")
                if sub:
                    return f"user:{sub}"
            except Exception:
                pass
            return f"token:{hashlib.sha256(token.encode()).hexdigest()[:16]}"

        forwarded = request.headers.get("X-Forwarded-For")
        ip = forwarded.split(",")[0].strip() if forwarded else (request.client.host if request.client else "unknown")
        return f"ip:{ip}"

    def _is_burst(self, request: Request) -> bool:
        return request.headers.get("X-Rate-Limit-Tier") == "burst"

    async def dispatch(self, request: Request, call_next: object) -> Response:  # type: ignore[override]
        # Health check is exempt
        if request.url.path in {"/health", "/docs", "/redoc", "/openapi.json"}:
            return await call_next(request)  # type: ignore[operator]

        key = self._identity(request)
        limit = self._burst_rpm if self._is_burst(request) else self._rpm
        window = self._windows[key]
        now = time.monotonic()
        cutoff = now - 60.0

        # Evict timestamps outside the window
        while window and window[0] < cutoff:
            window.popleft()

        remaining = limit - len(window)
        reset_at = int(window[0] + 60) if window else int(now + 60)

        if remaining <= 0:
            return JSONResponse(
                status_code=429,
                content={"error": {"code": "rate_limited", "message": "Too many requests"}},
                headers={
                    "Retry-After": str(reset_at - int(now)),
                    "X-RateLimit-Limit": str(limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(reset_at),
                },
            )

        window.append(now)
        response: Response = await call_next(request)  # type: ignore[operator]
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining - 1)
        response.headers["X-RateLimit-Reset"] = str(reset_at)
        return response
