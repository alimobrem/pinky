import uuid
from datetime import datetime

from sqlalchemy import Float, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from pinky_api.models.base import Base, TimestampMixin, gen_uuid


class WorkItem(Base, TimestampMixin):
    __tablename__ = "work_items"
    __table_args__ = (
        Index("idx_work_items_cluster", "cluster_id", "status"),
        Index("idx_work_items_owner", "owner_id", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=gen_uuid)
    issue_id: Mapped[uuid.UUID | None] = mapped_column(UUID, ForeignKey("issues.id"))
    cluster_id: Mapped[uuid.UUID] = mapped_column(UUID, ForeignKey("cluster_registry.id"), nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    why_now: Mapped[str | None] = mapped_column(String)
    recommended_next_step: Mapped[str | None] = mapped_column(String)
    status: Mapped[str] = mapped_column(String, server_default="ready")
    owner_id: Mapped[uuid.UUID | None] = mapped_column(UUID, ForeignKey("principals.id"))
    confidence: Mapped[float | None] = mapped_column(Float)
    priority: Mapped[str] = mapped_column(String, server_default="medium")
    labels: Mapped[dict] = mapped_column(JSONB, server_default="{}")
    annotations: Mapped[dict] = mapped_column(JSONB, server_default="{}")
    runbook_url: Mapped[str | None] = mapped_column(String)
    artifact_refs: Mapped[dict] = mapped_column(JSONB, server_default="{}")
    blocked_reason: Mapped[str | None] = mapped_column(String)
