import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from pinky_api.models.base import Base, gen_uuid


class Observation(Base):
    __tablename__ = "observations"
    __table_args__ = (
        Index("idx_observations_fingerprint", "fingerprint"),
        Index("idx_observations_cluster", "cluster_id", "observed_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=gen_uuid)
    cluster_id: Mapped[uuid.UUID] = mapped_column(UUID, ForeignKey("cluster_registry.id"), nullable=False)
    scanner: Mapped[str] = mapped_column(String, nullable=False)
    scanner_version: Mapped[str | None] = mapped_column(String)
    fingerprint: Mapped[str] = mapped_column(String, nullable=False)
    check_id: Mapped[str | None] = mapped_column(String)
    severity: Mapped[str] = mapped_column(String, nullable=False)
    resource_kind: Mapped[str | None] = mapped_column(String)
    resource_namespace: Mapped[str | None] = mapped_column(String)
    resource_name: Mapped[str | None] = mapped_column(String)
    payload: Mapped[dict] = mapped_column(JSONB, server_default="{}")
    observed_at: Mapped[datetime] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(server_default="now()")
