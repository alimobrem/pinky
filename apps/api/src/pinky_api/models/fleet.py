import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, LargeBinary, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from pinky_api.models.base import Base, TimestampMixin, gen_uuid


class ClusterRegistry(Base, TimestampMixin):
    __tablename__ = "cluster_registry"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=gen_uuid)
    display_name: Mapped[str] = mapped_column(String, nullable=False)
    api_endpoint: Mapped[str] = mapped_column(String, nullable=False)
    fleet_identifier: Mapped[str | None] = mapped_column(String)
    onboarding_state: Mapped[str] = mapped_column(String, server_default="pending")
    offboarding_state: Mapped[str | None] = mapped_column(String)


class ClusterObserverBinding(Base, TimestampMixin):
    __tablename__ = "cluster_observer_bindings"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=gen_uuid)
    cluster_id: Mapped[uuid.UUID] = mapped_column(UUID, ForeignKey("cluster_registry.id"), nullable=False)
    auth_method: Mapped[str] = mapped_column(String, nullable=False)
    health_state: Mapped[str] = mapped_column(String, server_default="unknown")
    last_observation_at: Mapped[datetime | None] = mapped_column()
    encrypted_credential: Mapped[bytes | None] = mapped_column(LargeBinary)
    rbac_scope: Mapped[dict] = mapped_column(JSONB, server_default="[]")


class ClusterIdentityBinding(Base, TimestampMixin):
    __tablename__ = "cluster_identity_bindings"
    __table_args__ = (UniqueConstraint("principal_id", "cluster_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=gen_uuid)
    principal_id: Mapped[uuid.UUID] = mapped_column(UUID, ForeignKey("principals.id"), nullable=False)
    cluster_id: Mapped[uuid.UUID] = mapped_column(UUID, ForeignKey("cluster_registry.id"), nullable=False)
    cluster_username: Mapped[str | None] = mapped_column(String)
    cluster_groups: Mapped[list] = mapped_column(JSONB, server_default="[]")
    binding_method: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, server_default="missing")
    encrypted_token: Mapped[bytes | None] = mapped_column(LargeBinary)
    expires_at: Mapped[datetime | None] = mapped_column()
