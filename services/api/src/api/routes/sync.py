import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.routes.auth import get_current_user
from src.db.session import get_db
from src.models.sync_config import SyncConfig
from src.models.user import User

router = APIRouter(prefix="/sync", tags=["sync"])


class SyncStatusResponse(BaseModel):
    id: uuid.UUID
    watch_path: str
    is_active: bool
    auto_sensitivity: str
    last_sync_at: Any

    model_config = {"from_attributes": True}


@router.get("/status", response_model=list[SyncStatusResponse])
async def sync_status(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Get sync configuration status for the tenant."""
    result = await db.execute(
        select(SyncConfig).where(SyncConfig.tenant_id == user.tenant_id)
    )
    return result.scalars().all()


@router.post("/trigger")
async def trigger_sync(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Manually trigger a sync for the tenant."""
    if user.role not in ("system_admin", "tenant_admin", "content_manager"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")

    try:
        from src.worker.celery_app import celery_app

        celery_app.send_task(
            "src.worker.tasks.sync.run_sync",
            args=[str(user.tenant_id)],
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to trigger sync: {e}",
        )

    return {"status": "sync_triggered"}
