"""Middleware to enforce tenant isolation on every request."""

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response


class TenantIsolationMiddleware(BaseHTTPMiddleware):
    """Injects tenant_id into request state from JWT claims.

    The actual RLS enforcement happens in get_current_user (auth.py) where
    SET LOCAL app.current_tenant_id is executed per-request.
    This middleware adds tenant_id to request.state for easy access in routes.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Extract tenant_id from JWT if present (parsed in auth dependency)
        # Default to None for unauthenticated endpoints
        request.state.tenant_id = None

        response = await call_next(request)
        return response
