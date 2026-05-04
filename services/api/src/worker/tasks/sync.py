"""Folder sync tasks for watchdog-based document ingestion."""

import hashlib
import os
from pathlib import Path

import structlog
from celery import shared_task

from src.core.config import settings

logger = structlog.get_logger()


@shared_task(name="src.worker.tasks.sync.run_sync")
def run_sync(tenant_id: str) -> dict:
    """Run folder sync for a tenant's configured watch paths."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session

    from src.models.document import Document
    from src.models.sync_config import SyncConfig

    engine = create_engine(settings.database_url_sync)
    new_files = 0
    updated_files = 0

    with Session(engine) as db:
        configs = db.query(SyncConfig).filter(
            SyncConfig.tenant_id == tenant_id,
            SyncConfig.is_active.is_(True),
        ).all()

        for config in configs:
            watch_path = Path(config.watch_path)
            if not watch_path.exists():
                logger.warning("watch_path_missing", path=str(watch_path), tenant_id=tenant_id)
                continue

            for file_path in watch_path.rglob("*"):
                if not file_path.is_file():
                    continue

                # Check file patterns
                if not _matches_patterns(file_path.name, config.file_patterns, config.exclude_patterns):
                    continue

                # Compute hash
                file_hash = _compute_file_hash(file_path)

                # Check if already indexed
                existing = db.query(Document).filter(
                    Document.tenant_id == tenant_id,
                    Document.file_hash == file_hash,
                    Document.deleted_at.is_(None),
                ).first()

                if existing:
                    continue

                # Upload to MinIO and create document record
                try:
                    from minio import Minio

                    import uuid

                    mc = Minio(
                        settings.minio_endpoint,
                        access_key=settings.minio_root_user,
                        secret_key=settings.minio_root_password,
                        secure=settings.minio_use_ssl,
                    )
                    bucket = f"tenant-{tenant_id}"
                    if not mc.bucket_exists(bucket):
                        mc.make_bucket(bucket)

                    minio_key = f"sync/{uuid.uuid4()}/{file_path.name}"
                    mc.fput_object(bucket, minio_key, str(file_path))

                    doc = Document(
                        tenant_id=tenant_id,
                        filename=file_path.name,
                        original_path=str(file_path),
                        file_size_bytes=file_path.stat().st_size,
                        file_hash=file_hash,
                        minio_bucket=bucket,
                        minio_key=minio_key,
                        status="pending",
                        sensitivity=config.auto_sensitivity,
                    )
                    db.add(doc)
                    db.flush()

                    # Trigger ingestion
                    from src.worker.celery_app import celery_app

                    celery_app.send_task(
                        "src.worker.tasks.ingestion.process_document",
                        args=[str(doc.id)],
                    )
                    new_files += 1

                except Exception as e:
                    logger.error("sync_file_failed", file=str(file_path), error=str(e))

            # Update last sync time
            from datetime import datetime, timezone

            config.last_sync_at = datetime.now(timezone.utc)

        db.commit()

    logger.info("sync_complete", tenant_id=tenant_id, new=new_files, updated=updated_files)
    return {"new_files": new_files, "updated_files": updated_files}


def _compute_file_hash(file_path: Path) -> str:
    """Compute SHA-256 hash of a file."""
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def _matches_patterns(
    filename: str,
    include_patterns: list[str],
    exclude_patterns: list[str],
) -> bool:
    """Check if filename matches include patterns and doesn't match exclude patterns."""
    import fnmatch

    # Check excludes first
    for pattern in exclude_patterns:
        if fnmatch.fnmatch(filename, pattern):
            return False

    # Check includes
    if include_patterns == ["*"]:
        return True

    return any(fnmatch.fnmatch(filename, p) for p in include_patterns)
