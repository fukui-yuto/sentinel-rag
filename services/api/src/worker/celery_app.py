"""Celery application configuration."""

from celery import Celery

from src.core.config import settings

celery_app = Celery(
    "sentinel-rag",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    result_expires=3600,
    task_routes={
        "src.worker.tasks.ingestion.*": {"queue": "ingestion"},
        "src.worker.tasks.embedding.*": {"queue": "embedding"},
        "src.worker.tasks.sync.*": {"queue": "sync"},
        "src.worker.tasks.audit_aggregator.*": {"queue": "audit"},
    },
    beat_schedule={
        "cleanup-deleted-documents": {
            "task": "src.worker.tasks.ingestion.cleanup_deleted_documents",
            "schedule": 86400.0,  # daily
        },
        "audit-log-integrity-check": {
            "task": "src.worker.tasks.audit_aggregator.verify_audit_chain",
            "schedule": 3600.0,  # hourly
        },
    },
)

celery_app.autodiscover_tasks(["src.worker.tasks"])

# Explicit imports to ensure task registration (autodiscover may not find submodules)
import src.worker.tasks.ingestion  # noqa: F401, E402
import src.worker.tasks.sync  # noqa: F401, E402
import src.worker.tasks.audit_aggregator  # noqa: F401, E402
