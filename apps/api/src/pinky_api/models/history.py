import uuid
from datetime import datetime

from sqlalchemy import String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from pinky_api.models.base import Base, gen_uuid


class HistoryEvent(Base):
    __tablename__ = "history_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=gen_uuid)
    aggregate_type: Mapped[str] = mapped_column(String, nullable=False)
    aggregate_id: Mapped[uuid.UUID] = mapped_column(UUID, nullable=False)
    event_type: Mapped[str] = mapped_column(String, nullable=False)
    cluster_id: Mapped[uuid.UUID | None] = mapped_column(UUID)
    principal_id: Mapped[uuid.UUID | None] = mapped_column(UUID)
    payload: Mapped[dict] = mapped_column(JSONB, server_default="{}")
    occurred_at: Mapped[datetime] = mapped_column(nullable=False)
