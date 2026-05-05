import uuid
from typing import Any, Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.routes.auth import get_current_user
from src.db.session import get_db
from src.models.audit_log import AuditLog
from src.models.document import Document
from src.models.llm_provider import LLMProvider
from src.models.qa_history import QAHistory
from src.models.user import User

logger = structlog.get_logger()

router = APIRouter(prefix="/admin", tags=["admin"])


# ---------------------------------------------------------------------------
# User Management
# ---------------------------------------------------------------------------
class UserCreateRequest(BaseModel):
    email: str
    display_name: str
    role: str = "user"


class UserUpdateRequest(BaseModel):
    display_name: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None


class UserResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    email: str
    display_name: str
    role: str
    is_active: bool
    last_login_at: Any
    created_at: Any

    model_config = {"from_attributes": True}


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role not in ("system_admin", "tenant_admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin required")
    return user


@router.get("/users", response_model=list[UserResponse])
async def list_users(
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> Any:
    result = await db.execute(
        select(User).where(User.tenant_id == user.tenant_id).order_by(User.email)
    )
    return result.scalars().all()


@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    data: UserCreateRequest,
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> Any:
    valid_roles = {"system_admin", "tenant_admin", "content_manager", "user", "auditor", "read_only"}
    if data.role not in valid_roles:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid role")

    if data.role == "system_admin" and user.role != "system_admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot create system_admin")

    existing = await db.execute(
        select(User).where(User.tenant_id == user.tenant_id, User.email == data.email)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User already exists")

    new_user = User(
        tenant_id=user.tenant_id,
        email=data.email,
        display_name=data.display_name,
        role=data.role,
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user


@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: uuid.UUID,
    data: UserUpdateRequest,
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> Any:
    valid_roles = {"system_admin", "tenant_admin", "content_manager", "user", "auditor", "read_only"}
    if data.role is not None:
        if data.role not in valid_roles:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid role")
        if data.role == "system_admin" and user.role != "system_admin":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot assign system_admin role")

    result = await db.execute(
        select(User).where(User.id == user_id, User.tenant_id == user.tenant_id)
    )
    target = result.scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(target, field, value)

    await db.commit()
    await db.refresh(target)
    return target


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: uuid.UUID,
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Deactivate a user (soft delete by setting is_active=False)."""
    result = await db.execute(
        select(User).where(User.id == user_id, User.tenant_id == user.tenant_id)
    )
    target = result.scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if target.id == user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot delete yourself")
    target.is_active = False
    await db.commit()


# ---------------------------------------------------------------------------
# LLM Provider Management
# ---------------------------------------------------------------------------
class ProviderResponse(BaseModel):
    id: uuid.UUID
    name: str
    display_name: str
    provider_type: str
    is_enabled: bool
    config: dict

    model_config = {"from_attributes": True}


class ProviderUpdateRequest(BaseModel):
    is_enabled: Optional[bool] = None
    config: Optional[dict] = None


@router.get("/providers", response_model=list[ProviderResponse])
async def list_providers(
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> Any:
    result = await db.execute(select(LLMProvider).order_by(LLMProvider.name))
    return result.scalars().all()


@router.put("/providers/{provider_id}", response_model=ProviderResponse)
async def update_provider(
    provider_id: uuid.UUID,
    data: ProviderUpdateRequest,
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> Any:
    if user.role != "system_admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="System admin required")

    result = await db.execute(select(LLMProvider).where(LLMProvider.id == provider_id))
    provider = result.scalar_one_or_none()
    if not provider:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Provider not found")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(provider, field, value)

    await db.commit()
    await db.refresh(provider)
    return provider


# ---------------------------------------------------------------------------
# Audit Log
# ---------------------------------------------------------------------------
class AuditLogResponse(BaseModel):
    id: int
    tenant_id: Optional[uuid.UUID]
    user_id: Optional[uuid.UUID]
    category: str
    action: str
    resource_type: Optional[str]
    resource_id: Optional[str]
    details: dict
    ip_address: Optional[str]
    result: str
    created_at: Any

    model_config = {"from_attributes": True}


def require_admin_or_auditor(user: User = Depends(get_current_user)) -> User:
    if user.role not in ("system_admin", "tenant_admin", "auditor"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin or auditor required")
    return user


@router.get("/audit-logs", response_model=list[AuditLogResponse])
async def list_audit_logs(
    category: Optional[str] = None,
    action: Optional[str] = None,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    user: User = Depends(require_admin_or_auditor),
    db: AsyncSession = Depends(get_db),
) -> Any:

    query = select(AuditLog)
    if user.role != "system_admin":
        query = query.where(AuditLog.tenant_id == user.tenant_id)
    if category:
        query = query.where(AuditLog.category == category)
    if action:
        query = query.where(AuditLog.action == action)

    query = query.order_by(AuditLog.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


# ---------------------------------------------------------------------------
# System Health & Metrics
# ---------------------------------------------------------------------------
@router.get("/health")
async def system_health(
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """System-level health status for admin dashboard."""
    total_docs = (await db.execute(select(func.count(Document.id)))).scalar() or 0
    total_users = (await db.execute(select(func.count(User.id)))).scalar() or 0
    total_queries = (await db.execute(select(func.count(QAHistory.id)))).scalar() or 0

    return {
        "status": "ok",
        "stats": {
            "total_documents": total_docs,
            "total_users": total_users,
            "total_queries": total_queries,
        },
    }


@router.get("/metrics")
async def usage_metrics(
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Usage statistics for the admin dashboard."""
    from datetime import datetime, timedelta, timezone

    since = datetime.now(timezone.utc) - timedelta(days=30)
    recent_queries = (
        await db.execute(
            select(func.count(QAHistory.id)).where(QAHistory.created_at >= since)
        )
    ).scalar() or 0

    return {
        "period": "last_30_days",
        "queries": recent_queries,
    }


@router.post("/reindex")
async def reindex_documents(
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Re-index all documents (e.g. after changing embedding provider)."""
    if user.role != "system_admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="System admin required")

    result = await db.execute(
        select(Document).where(
            Document.tenant_id == user.tenant_id,
            Document.deleted_at.is_(None),
            Document.status.in_(["indexed", "failed"]),
        )
    )
    docs = result.scalars().all()

    queued = 0
    failed = 0
    for doc in docs:
        try:
            from src.worker.celery_app import celery_app
            celery_app.send_task(
                "src.worker.tasks.ingestion.process_document",
                args=[str(doc.id)],
            )
            doc.status = "pending"
            doc.chunk_count = 0
            queued += 1
        except Exception as e:
            logger.error("reindex_task_send_failed", doc_id=str(doc.id), error=str(e))
            failed += 1

    await db.commit()
    return {"queued": queued, "failed": failed, "total": len(docs)}
