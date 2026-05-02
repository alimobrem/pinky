import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from pinky_api.models.base import Base, gen_uuid


class Execution(Base):
    __tablename__ = "executions"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=gen_uuid)
    work_item_id: Mapped[uuid.UUID | None] = mapped_column(UUID, ForeignKey("work_items.id"))
    cluster_id: Mapped[uuid.UUID] = mapped_column(UUID, ForeignKey("cluster_registry.id"), nullable=False)
    execution_type: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, server_default="pending")
    started_at: Mapped[datetime | None] = mapped_column()
    completed_at: Mapped[datetime | None] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(server_default="now()")


class ExecutionEvent(Base):
    __tablename__ = "execution_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=gen_uuid)
    execution_id: Mapped[uuid.UUID] = mapped_column(UUID, nullable=False)
    event_type: Mapped[str] = mapped_column(String, nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, server_default="{}")
    occurred_at: Mapped[datetime] = mapped_column(nullable=False)


class Approval(Base):
    __tablename__ = "approvals"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=gen_uuid)
    execution_id: Mapped[uuid.UUID] = mapped_column(UUID, ForeignKey("executions.id"), nullable=False)
    approver_id: Mapped[uuid.UUID | None] = mapped_column(UUID, ForeignKey("principals.id"))
    changeset_digest: Mapped[str] = mapped_column(String, nullable=False)
    target_resources: Mapped[list] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(String, server_default="pending")
    expires_at: Mapped[datetime] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(server_default="now()")
