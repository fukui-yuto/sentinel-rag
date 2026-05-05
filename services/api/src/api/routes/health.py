from typing import Any

import redis.asyncio as aioredis
import structlog
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.db.session import get_db

logger = structlog.get_logger()

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check() -> dict[str, str]:
    """Basic liveness probe."""
    return {"status": "ok"}


@router.get("/health/ready")
async def readiness_check(db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    """Readiness probe: checks all dependent services."""
    checks: dict[str, Any] = {}

    # PostgreSQL
    try:
        await db.execute(text("SELECT 1"))
        checks["postgres"] = "ok"
    except Exception as e:
        logger.warning("health_check_failed", service="postgres", error=str(e))
        checks["postgres"] = "error"

    # Redis
    try:
        r = aioredis.from_url(settings.redis_url, socket_connect_timeout=3)
        await r.ping()
        await r.aclose()
        checks["redis"] = "ok"
    except Exception as e:
        logger.warning("health_check_failed", service="redis", error=str(e))
        checks["redis"] = "error"

    # Qdrant
    try:
        from qdrant_client import AsyncQdrantClient

        qc = AsyncQdrantClient(
            host=settings.qdrant_host,
            port=settings.qdrant_port,
            api_key=settings.qdrant_api_key or None,
            https=False,
            timeout=5,
        )
        await qc.get_collections()
        await qc.close()
        checks["qdrant"] = "ok"
    except Exception as e:
        logger.warning("health_check_failed", service="qdrant", error=str(e))
        checks["qdrant"] = "error"

    # MinIO
    try:
        from minio import Minio

        mc = Minio(
            settings.minio_endpoint,
            access_key=settings.minio_root_user,
            secret_key=settings.minio_root_password,
            secure=settings.minio_use_ssl,
        )
        mc.list_buckets()
        checks["minio"] = "ok"
    except Exception as e:
        logger.warning("health_check_failed", service="minio", error=str(e))
        checks["minio"] = "error"

    all_ok = all(v == "ok" for v in checks.values())
    return {"status": "ready" if all_ok else "degraded", "checks": checks}
