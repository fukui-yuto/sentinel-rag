import hashlib
import uuid
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.routes.auth import get_current_user
from src.db.session import get_db
from src.models.document import Document, DocumentChunk
from src.models.user import User

router = APIRouter(prefix="/documents", tags=["documents"])


class DocumentResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    filename: str
    mime_type: Optional[str]
    file_size_bytes: int
    status: str
    sensitivity: str
    chunk_count: int
    doc_metadata: dict
    created_at: Any
    updated_at: Any

    model_config = {"from_attributes": True}


class DocumentListResponse(BaseModel):
    items: list[DocumentResponse]
    total: int
    page: int
    page_size: int


@router.get("", response_model=DocumentListResponse)
async def list_documents(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: Optional[str] = Query(None, alias="status"),
    sensitivity: Optional[str] = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """List documents within the user's tenant scope."""
    query = select(Document).where(
        Document.tenant_id == user.tenant_id,
        Document.deleted_at.is_(None),
    )

    if status_filter:
        query = query.where(Document.status == status_filter)
    if sensitivity:
        query = query.where(Document.sensitivity == sensitivity)

    # Count
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    # Paginate
    query = query.order_by(Document.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    docs = result.scalars().all()

    return DocumentListResponse(
        items=[DocumentResponse.model_validate(d) for d in docs],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile,
    sensitivity: str = "internal",
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Upload a document for processing."""
    if user.role == "read_only":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Upload not allowed")

    if sensitivity not in ("public", "internal", "confidential", "restricted"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid sensitivity")

    # Read file content with size limit (100 MB)
    max_size = 100 * 1024 * 1024
    content = await file.read(max_size + 1)
    if len(content) > max_size:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Maximum size is {max_size // (1024*1024)} MB",
        )
    file_hash = hashlib.sha256(content).hexdigest()

    # Check duplicate
    existing = await db.execute(
        select(Document).where(
            Document.tenant_id == user.tenant_id,
            Document.file_hash == file_hash,
            Document.deleted_at.is_(None),
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Document with identical content already exists",
        )

    # Store in MinIO
    from minio import Minio

    from src.core.config import settings

    mc = Minio(
        settings.minio_endpoint,
        access_key=settings.minio_root_user,
        secret_key=settings.minio_root_password,
        secure=settings.minio_use_ssl,
    )
    bucket = f"tenant-{user.tenant_id}"
    if not mc.bucket_exists(bucket):
        mc.make_bucket(bucket)

    minio_key = f"documents/{uuid.uuid4()}/{file.filename}"
    import io

    mc.put_object(bucket, minio_key, io.BytesIO(content), len(content))

    # Create DB record
    doc = Document(
        tenant_id=user.tenant_id,
        uploaded_by=user.id,
        filename=file.filename or "unknown",
        mime_type=file.content_type,
        file_size_bytes=len(content),
        file_hash=file_hash,
        minio_bucket=bucket,
        minio_key=minio_key,
        status="pending",
        sensitivity=sensitivity,
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    # Dispatch ingestion task
    try:
        from src.worker.celery_app import celery_app

        celery_app.send_task(
            "src.worker.tasks.ingestion.process_document",
            args=[str(doc.id)],
        )
    except Exception:
        pass  # Worker may not be running in dev

    return doc


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Get document details."""
    result = await db.execute(
        select(Document).where(
            Document.id == document_id,
            Document.tenant_id == user.tenant_id,
            Document.deleted_at.is_(None),
        )
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return doc


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Soft-delete a document."""
    result = await db.execute(
        select(Document).where(
            Document.id == document_id,
            Document.tenant_id == user.tenant_id,
            Document.deleted_at.is_(None),
        )
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    # Permission check: content_manager+ or owner
    if user.role not in ("system_admin", "tenant_admin", "content_manager"):
        if doc.uploaded_by != user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")

    from datetime import datetime, timezone

    doc.deleted_at = datetime.now(timezone.utc)
    doc.status = "deleted"
    await db.commit()


class ChunkResponse(BaseModel):
    id: uuid.UUID
    chunk_index: int
    content: str
    token_count: int
    created_at: Any

    model_config = {"from_attributes": True}


@router.get("/{document_id}/chunks", response_model=list[ChunkResponse])
async def get_document_chunks(
    document_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Get all chunks for a document."""
    # Verify document belongs to user's tenant
    result = await db.execute(
        select(Document).where(
            Document.id == document_id,
            Document.tenant_id == user.tenant_id,
            Document.deleted_at.is_(None),
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    chunks = await db.execute(
        select(DocumentChunk)
        .where(DocumentChunk.document_id == document_id)
        .order_by(DocumentChunk.chunk_index)
    )
    return chunks.scalars().all()
