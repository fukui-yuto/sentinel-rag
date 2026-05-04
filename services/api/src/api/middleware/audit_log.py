"""Middleware for automatic audit logging of API requests."""

import hashlib
import json
import time
from typing import Optional

import structlog
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

logger = structlog.get_logger()

# Paths that don't need audit logging
SKIP_PATHS = {"/api/v1/health", "/api/v1/health/ready", "/health"}


class AuditLogMiddleware(BaseHTTPMiddleware):
    """Log all API requests for audit trail."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.url.path in SKIP_PATHS:
            return await call_next(request)

        start = time.monotonic()
        response = await call_next(request)
        duration_ms = int((time.monotonic() - start) * 1000)

        # Log request details
        await logger.ainfo(
            "api_request",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=duration_ms,
            ip=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent", ""),
        )

        return response
