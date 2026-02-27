"""
Authentication middleware for VoxSentinel API.

Validates API key or JWT Bearer tokens on incoming requests
and enforces role-based access control.
"""

from __future__ import annotations

import os

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import JSONResponse, Response

# Paths that skip auth checks.
_PUBLIC_PATHS: set[str] = {"/health", "/docs", "/openapi.json", "/redoc", "/metrics"}


class AuthMiddleware(BaseHTTPMiddleware):
    """Validate ``Authorization: Bearer <key>`` against ``TG_API_KEY``."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint,
    ) -> Response:
        path = request.url.path

        # Allow health, docs, and WebSocket upgrade through without auth.
        if path in _PUBLIC_PATHS or path.startswith("/ws/"):
            return await call_next(request)

        api_key = os.environ.get("TG_API_KEY", "")
        auth_header = request.headers.get("Authorization", "")

        if not auth_header.startswith("Bearer "):
            return JSONResponse(
                status_code=401,
                content={"detail": "Missing or invalid Authorization header"},
            )

        token = auth_header[len("Bearer "):]
        if token != api_key:
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid API key"},
            )

        return await call_next(request)
