from __future__ import annotations

from collections import defaultdict, deque
from hashlib import sha256
from threading import Lock
from time import monotonic
from typing import Deque, Dict

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.core.config import settings


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault(
            "Permissions-Policy",
            "camera=(), microphone=(), geolocation=(), payment=(), usb=()",
        )
        response.headers.setdefault("Cache-Control", "no-store")
        if settings.APP_ENV.value == "prod":
            response.headers.setdefault(
                "Strict-Transport-Security",
                "max-age=31536000; includeSubDomains",
            )
        return response


class RequestGuardMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self._requests: Dict[str, Deque[float]] = defaultdict(deque)
        self._lock = Lock()

    @staticmethod
    def _rate_limit(request: Request) -> tuple[int, str] | None:
        path = request.url.path
        if request.method == "POST" and path in {
            "/auth/login/password",
            "/auth/signup/password",
            "/auth/google/set-session",
        }:
            return settings.AUTH_RATE_LIMIT_PER_MINUTE, "auth"
        if request.method == "POST" and path == "/auth/refresh":
            return 60, "refresh"
        if request.method == "POST" and (
            path.endswith("/chat") or path.endswith("/branch")
        ):
            return settings.LLM_RATE_LIMIT_PER_MINUTE, "llm"
        if path.startswith("/health/llm"):
            return 5, "llm-health"
        return None

    @staticmethod
    def _client_key(request: Request) -> str:
        authorization = request.headers.get("authorization", "")
        if authorization.lower().startswith("bearer "):
            digest = sha256(authorization.encode("utf-8")).hexdigest()[:24]
            return f"token:{digest}"
        host = request.client.host if request.client else "unknown"
        return f"ip:{host}"

    async def dispatch(self, request: Request, call_next):
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                if int(content_length) > settings.MAX_REQUEST_BODY_BYTES:
                    return JSONResponse(
                        status_code=413,
                        content={"detail": {"code": "REQUEST_TOO_LARGE", "message": "Request body is too large."}},
                    )
            except ValueError:
                return JSONResponse(status_code=400, content={"detail": "Invalid Content-Length header."})

        rate_rule = self._rate_limit(request)
        if rate_rule:
            limit, bucket_name = rate_rule
            now = monotonic()
            bucket_key = f"{self._client_key(request)}:{bucket_name}"
            with self._lock:
                bucket = self._requests[bucket_key]
                while bucket and bucket[0] <= now - 60:
                    bucket.popleft()
                if len(bucket) >= limit:
                    return JSONResponse(
                        status_code=429,
                        headers={"Retry-After": "60"},
                        content={"detail": {"code": "RATE_LIMITED", "message": "Too many requests. Try again later."}},
                    )
                bucket.append(now)

        return await call_next(request)
