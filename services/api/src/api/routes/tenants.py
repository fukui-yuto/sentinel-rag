import uuid
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.routes.auth import get_current_user
from src.db.session import get_db
from src.models.tenant import Tenant
from src.models.user import User

router = APIRouter(prefix="/admin/tenants", tags=["admin-tenants"])


class TenantCreate(BaseModel):
    name: str
    slug: str
    max_storage_bytes: int = 53687091200
    max_documents: int = 10000


class TenantUpdate(BaseModel):
    name: Optional[str] = None
    is_active: Optional[bool] = None
    max_storage_bytes: Optional[int] = None
    max_documents: Optional[int] = None
    settings: Optional[dict] = None


class TenantResponse(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    is_active: bool
    max_storage_bytes: int
    max_documents: int
    settings: dict
    created_at: Any
    updated_at: Any

    model_config = {"from_attributes": True}


def require_system_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "system_admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="System admin required")
    return user


@router.get("", response_model=list[TenantResponse])
async def list_tenants(
    user: User = Depends(require_system_admin),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """List all tenants (system_admin only)."""
    # Bypass RLS by not setting tenant context
    result = await db.execute(select(Tenant).order_by(Tenant.name))
    return result.scalars().all()


@router.post("", response_model=TenantResponse, status_code=status.HTTP_201_CREATED)
async def create_tenant(
    data: TenantCreate,
    user: User = Depends(require_system_admin),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Create a new tenant."""
    # Check uniqueness
    existing = await db.execute(
        select(Tenant).where((Tenant.name == data.name) | (Tenant.slug == data.slug))
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Tenant already exists")

    tenant = Tenant(**data.model_dump())
    db.add(tenant)
    await db.commit()
    await db.refresh(tenant)

    # Create Qdrant collection for tenant
    try:
        from qdrant_client import QdrantClient
        from qdrant_client.models import Distance, VectorParams

        from src.core.config import settings

        qc = QdrantClient(
            host=settings.qdrant_host,
            port=settings.qdrant_port,
            api_key=settings.qdrant_api_key or None,
        )
        qc.create_collection(
            collection_name=f"tenant_{tenant.slug}",
            vectors_config=VectorParams(size=768, distance=Distance.COSINE),
        )
    except Exception:
        pass

    # Create MinIO bucket
    try:
        from minio import Minio

        from src.core.config import settings

        mc = Minio(
            settings.minio_endpoint,
            access_key=settings.minio_root_user,
            secret_key=settings.minio_root_password,
            secure=settings.minio_use_ssl,
        )
        bucket = f"tenant-{tenant.id}"
        if not mc.bucket_exists(bucket):
            mc.make_bucket(bucket)
    except Exception:
        pass

    return tenant


@router.get("/{tenant_id}", response_model=TenantResponse)
async def get_tenant(
    tenant_id: uuid.UUID,
    user: User = Depends(require_system_admin),
    db: AsyncSession = Depends(get_db),
) -> Any:
    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    return tenant


@router.put("/{tenant_id}", response_model=TenantResponse)
async def update_tenant(
    tenant_id: uuid.UUID,
    data: TenantUpdate,
    user: User = Depends(require_system_admin),
    db: AsyncSession = Depends(get_db),
) -> Any:
    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(tenant, field, value)

    await db.commit()
    await db.refresh(tenant)
    return tenant


@router.delete("/{tenant_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tenant(
    tenant_id: uuid.UUID,
    user: User = Depends(require_system_admin),
    db: AsyncSession = Depends(get_db),
) -> None:
    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")

    await db.delete(tenant)
    await db.commit()
