"""Sentinel RAG Platform - FastAPI Application."""

from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.middleware.audit_log import AuditLogMiddleware
from src.api.middleware.rate_limit import RateLimitMiddleware
from src.api.middleware.tenant_isolation import TenantIsolationMiddleware
from src.api.routes import admin, auth, documents, health, qa, sync, tenants
from src.core.config import settings

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer() if settings.is_development else structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(0),
)

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info("application_startup", environment=settings.environment)
    yield
    logger.info("application_shutdown")


app = FastAPI(
    title="Sentinel RAG Platform",
    description="Enterprise RAG platform with multi-tenant support",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/api/docs" if settings.is_development else None,
    redoc_url="/api/redoc" if settings.is_development else None,
)

# --- Middleware (order matters: last added = first executed) ---
app.add_middleware(AuditLogMiddleware)
app.add_middleware(RateLimitMiddleware, requests_per_minute=60)
app.add_middleware(TenantIsolationMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[f"https://{settings.allowed_hosts}"] if not settings.is_development else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Routes ---
prefix = settings.api_v1_prefix

app.include_router(health.router, prefix=prefix)
app.include_router(auth.router, prefix=prefix)
app.include_router(documents.router, prefix=prefix)
app.include_router(qa.router, prefix=prefix)
app.include_router(sync.router, prefix=prefix)
app.include_router(tenants.router, prefix=prefix)
app.include_router(admin.router, prefix=prefix)
