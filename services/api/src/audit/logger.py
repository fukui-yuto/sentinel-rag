"""Audit log writer with hash chain support."""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.audit.hash_chain import compute_record_hash
from src.models.audit_log import AuditLog


async def write_audit_log(
    db: AsyncSession,
    category: str,
    action: str,
    tenant_id: Optional[str] = None,
    user_id: Optional[str] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    details: Optional[dict] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    result: str = "success",
) -> AuditLog:
    """Write an audit log entry with hash chain linkage."""
    now = datetime.now(timezone.utc)

    # Get previous hash
    prev = await db.execute(
        select(AuditLog.record_hash)
        .order_by(AuditLog.id.desc())
        .limit(1)
    )
    previous_hash = prev.scalar_one_or_none()

    record_hash = compute_record_hash(
        created_at=now.isoformat(),
        user_id=user_id,
        tenant_id=tenant_id,
        category=category,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details=details or {},
        result=result,
        previous_hash=previous_hash,
    )

    entry = AuditLog(
        tenant_id=tenant_id,
        user_id=user_id,
        category=category,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details=details or {},
        ip_address=ip_address,
        user_agent=user_agent,
        result=result,
        previous_hash=previous_hash,
        record_hash=record_hash,
        created_at=now,
    )
    db.add(entry)
    await db.flush()
    return entry
