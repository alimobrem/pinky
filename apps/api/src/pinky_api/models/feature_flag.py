import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from pinky_api.models.base import Base, gen_uuid


class FeatureFlag(Base):
    __tablename__ = "feature_flags"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=gen_uuid)
    flag_name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, server_default="false", nullable=False)
    scope_type: Mapped[str] = mapped_column(String(20), server_default="global", nullable=False)
    scope_id: Mapped[uuid.UUID | None] = mapped_column(UUID)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default="now()"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default="now()"
    )
