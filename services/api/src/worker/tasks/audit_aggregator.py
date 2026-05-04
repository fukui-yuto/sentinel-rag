"""Audit log aggregation and integrity verification tasks."""

import structlog
from celery import shared_task

from src.core.config import settings

logger = structlog.get_logger()


@shared_task(name="src.worker.tasks.audit_aggregator.verify_audit_chain")
def verify_audit_chain() -> dict:
    """Verify the integrity of the audit log hash chain."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session

    from src.audit.hash_chain import verify_chain
    from src.models.audit_log import AuditLog

    engine = create_engine(settings.database_url_sync)

    with Session(engine) as db:
        # Check last 1000 records
        logs = (
            db.query(AuditLog)
            .order_by(AuditLog.id.asc())
            .limit(1000)
            .all()
        )

        if not logs:
            return {"status": "ok", "checked": 0}

        records = [
            {
                "created_at": log.created_at.isoformat(),
                "user_id": str(log.user_id) if log.user_id else None,
                "tenant_id": str(log.tenant_id) if log.tenant_id else None,
                "category": log.category,
                "action": log.action,
                "resource_type": log.resource_type,
                "resource_id": log.resource_id,
                "details": log.details,
                "result": log.result,
                "previous_hash": log.previous_hash,
                "record_hash": log.record_hash,
            }
            for log in logs
        ]

        is_valid, broken_at = verify_chain(records)

        if not is_valid:
            logger.error("audit_chain_broken", broken_at_index=broken_at)
            return {"status": "broken", "broken_at_index": broken_at, "checked": len(records)}

        logger.info("audit_chain_verified", checked=len(records))
        return {"status": "ok", "checked": len(records)}
