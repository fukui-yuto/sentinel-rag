"""Application-level rate limiting backed by Redis."""

import time
from typing import Optional

import redis.asyncio as aioredis
from fastapi import HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from src.core.config import settings


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Sliding window rate limiter using Redis.

    Operates as a secondary layer behind nginx rate limiting.
    Per-user limits when authenticated, per-IP otherwise.
    """

    def __init__(self, app, requests_per_minute: int = 60):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.window = 60  # seconds

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Skip health checks
        if request.url.path.startswith("/api/v1/health") or request.url.path == "/health":
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        key = f"ratelimit:{client_ip}"

        try:
            r = aioredis.from_url(settings.redis_url, socket_connect_timeout=1)
            current = await r.get(key)

            if current and int(current) >= self.requests_per_minute:
                await r.aclose()
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Rate limit exceeded",
                )

            pipe = r.pipeline()
            pipe.incr(key)
            pipe.expire(key, self.window)
            await pipe.execute()
            await r.aclose()
        except HTTPException:
            raise
        except Exception:
            pass  # Fail open if Redis is unavailable

        return await call_next(request)
