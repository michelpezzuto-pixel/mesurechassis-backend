"""Custom middlewares (security headers, login rate-limit)."""
from __future__ import annotations

import time
from collections import defaultdict, deque
from typing import Deque, Dict

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response


# ── Security headers ─────────────────────────────────────────────────────
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Adds baseline HTTP security headers to every response.

    Note: HSTS is only emitted when the request was served over HTTPS
    (proxy-aware via `request.url.scheme`) to avoid breaking local HTTP dev.
    """

    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault(
            "Permissions-Policy",
            "geolocation=(), microphone=(self), camera=(self)",
        )
        # Only emit HSTS on confirmed HTTPS to avoid breaking local plain-HTTP dev
        forwarded_proto = request.headers.get("x-forwarded-proto", "").lower()
        if request.url.scheme == "https" or forwarded_proto == "https":
            response.headers.setdefault(
                "Strict-Transport-Security",
                "max-age=31536000; includeSubDomains",
            )
        return response


# ── Login rate-limit ─────────────────────────────────────────────────────
class LoginRateLimitMiddleware(BaseHTTPMiddleware):
    """Simple in-memory per-IP sliding-window rate limit for /api/auth/login.

    NOT for production at scale (use Redis + slowapi for that) — but it's
    enough to stop trivial credential stuffing in our current single-pod
    deployment and is a strict improvement over zero throttling.
    """

    def __init__(self, app, max_attempts: int, window_sec: int):
        super().__init__(app)
        self.max_attempts = max_attempts
        self.window_sec = window_sec
        self._hits: Dict[str, Deque[float]] = defaultdict(deque)

    def _client_ip(self, request: Request) -> str:
        # Prefer X-Forwarded-For first hop (proxy/ingress sets it).
        xff = request.headers.get("x-forwarded-for", "")
        if xff:
            return xff.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    async def dispatch(self, request: Request, call_next):
        is_login = (
            request.method == "POST"
            and request.url.path.rstrip("/") == "/api/auth/login"
        )
        if is_login:
            ip = self._client_ip(request)
            now = time.time()
            bucket = self._hits[ip]
            # Drop hits outside the window
            while bucket and now - bucket[0] > self.window_sec:
                bucket.popleft()
            if len(bucket) >= self.max_attempts:
                retry_after = int(self.window_sec - (now - bucket[0]))
                return JSONResponse(
                    status_code=429,
                    content={
                        "detail": (
                            f"Trop de tentatives. Réessayez dans {max(retry_after, 1)}s."
                        )
                    },
                    headers={"Retry-After": str(max(retry_after, 1))},
                )
            bucket.append(now)
        return await call_next(request)
