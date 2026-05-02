import uuid
from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, Integer, LargeBinary, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from pinky_api.models.base import Base, TimestampMixin, gen_uuid


class Definition(Base, TimestampMixin):
    __tablename__ = "definitions"
    __table_args__ = (UniqueConstraint("kind", "name"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=gen_uuid)
    kind: Mapped[str] = mapped_column(String, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    version: Mapped[str] = mapped_column(String, server_default="1.0.0")
    frontmatter: Mapped[dict] = mapped_column(JSONB, nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, server_default="true")
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID, ForeignKey("principals.id"))


class ServiceBinding(Base, TimestampMixin):
    __tablename__ = "service_bindings"
    __table_args__ = (UniqueConstraint("name", "cluster_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=gen_uuid)
    name: Mapped[str] = mapped_column(String, nullable=False)
    service_type: Mapped[str] = mapped_column(String, nullable=False)
    cluster_id: Mapped[uuid.UUID | None] = mapped_column(UUID, ForeignKey("cluster_registry.id"))
    base_url: Mapped[str] = mapped_column(String, nullable=False)
    auth_method: Mapped[str] = mapped_column(String, nullable=False)
    encrypted_credential: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    health_state: Mapped[str] = mapped_column(String, server_default="unknown")
    last_check_at: Mapped[datetime | None] = mapped_column()
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID, ForeignKey("principals.id"))


class DomainEvent(Base):
    __tablename__ = "domain_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=gen_uuid)
    event_type: Mapped[str] = mapped_column(String, nullable=False)
    aggregate_type: Mapped[str] = mapped_column(String, nullable=False)
    aggregate_id: Mapped[uuid.UUID] = mapped_column(UUID, nullable=False)
    cluster_id: Mapped[uuid.UUID | None] = mapped_column(UUID)
    principal_id: Mapped[uuid.UUID | None] = mapped_column(UUID)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(server_default="now()")


class WebhookSubscription(Base, TimestampMixin):
    __tablename__ = "webhook_subscriptions"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=gen_uuid)
    name: Mapped[str] = mapped_column(String, nullable=False)
    url: Mapped[str] = mapped_column(String, nullable=False)
    event_patterns: Mapped[list] = mapped_column(ARRAY(String), nullable=False)
    formatter: Mapped[str] = mapped_column(String, server_default="generic")
    channel_config: Mapped[dict] = mapped_column(JSONB, server_default="{}")
    secret_hash: Mapped[str | None] = mapped_column(String)
    enabled: Mapped[bool] = mapped_column(Boolean, server_default="true")
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID, ForeignKey("principals.id"))


class WebhookDelivery(Base):
    __tablename__ = "webhook_deliveries"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=gen_uuid)
    subscription_id: Mapped[uuid.UUID] = mapped_column(UUID, ForeignKey("webhook_subscriptions.id"), nullable=False)
    domain_event_id: Mapped[uuid.UUID] = mapped_column(UUID, ForeignKey("domain_events.id"), nullable=False)
    status: Mapped[str] = mapped_column(String, server_default="pending")
    attempts: Mapped[int] = mapped_column(Integer, server_default="0")
    last_attempt_at: Mapped[datetime | None] = mapped_column()
    last_response_code: Mapped[int | None] = mapped_column(Integer)
    next_retry_at: Mapped[datetime | None] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(server_default="now()")


class PolicyRule(Base, TimestampMixin):
    __tablename__ = "policy_rules"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=gen_uuid)
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(String)
    priority: Mapped[int] = mapped_column(Integer, server_default="100")
    enabled: Mapped[bool] = mapped_column(Boolean, server_default="true")
    conditions: Mapped[dict] = mapped_column(JSONB, nullable=False)
    action: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID, ForeignKey("principals.id"))


class ApiToken(Base):
    __tablename__ = "api_tokens"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=gen_uuid)
    principal_id: Mapped[uuid.UUID] = mapped_column(UUID, ForeignKey("principals.id"), nullable=False)
    token_hash: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    scopes: Mapped[list] = mapped_column(ARRAY(String), server_default="{}")
    expires_at: Mapped[datetime | None] = mapped_column()
    last_used_at: Mapped[datetime | None] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(server_default="now()")
    revoked_at: Mapped[datetime | None] = mapped_column()


class ProjectionCursor(Base):
    __tablename__ = "projection_cursors"

    workflow_id: Mapped[str] = mapped_column(String, primary_key=True)
    last_event_id: Mapped[int] = mapped_column(Integer, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(server_default="now()")
