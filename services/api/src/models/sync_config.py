import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base, TenantMixin, TimestampMixin


class SyncConfig(Base, TenantMixin, TimestampMixin):
    __tablename__ = "sync_configs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    watch_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    auto_sensitivity: Mapped[str] = mapped_column(String(50), default="internal", nullable=False)
    file_patterns: Mapped[list] = mapped_column(JSONB, default=lambda: ["*"], nullable=False)
    exclude_patterns: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    last_sync_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
