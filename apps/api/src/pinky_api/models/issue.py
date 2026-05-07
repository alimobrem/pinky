import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from pinky_api.models.base import Base, TimestampMixin, gen_uuid


class Issue(Base, TimestampMixin):
    __tablename__ = "issues"
    __table_args__ = (
        Index("idx_issues_correlation", "correlation_key"),
        Index("idx_issues_cluster", "cluster_id", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=gen_uuid)
    cluster_id: Mapped[uuid.UUID] = mapped_column(UUID, ForeignKey("cluster_registry.id"), nullable=False)
    correlation_key: Mapped[str] = mapped_column(String, nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    severity: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, server_default="open")
    labels: Mapped[dict] = mapped_column(JSONB, server_default="{}")
    annotations: Mapped[dict] = mapped_column(JSONB, server_default="{}")
    runbook_url: Mapped[str | None] = mapped_column(String)
    first_seen_at: Mapped[datetime] = mapped_column(nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column()
    resolved_by: Mapped[str | None] = mapped_column(String)
    suppressed_until: Mapped[datetime | None] = mapped_column()
