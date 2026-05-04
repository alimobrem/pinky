"""Webhook repository — subscription CRUD and delivery tracking."""

from uuid import UUID

from sqlalchemy import delete as sa_delete
from sqlalchemy import select

from pinky_api.models.extensibility import DomainEvent, WebhookDelivery, WebhookSubscription
from pinky_api.repositories.base import BaseRepository


class WebhookRepository(BaseRepository):
    async def list_subscriptions(self, limit: int = 50, cursor: str | None = None) -> dict:
        stmt = select(WebhookSubscription)
        return await self.paginate(stmt, WebhookSubscription, limit=limit, cursor=cursor)

    async def create_subscription(self, **kwargs: object) -> WebhookSubscription:
        sub = WebhookSubscription(**kwargs)
        self.session.add(sub)
        await self.session.flush()
        return sub

    async def delete_subscription(self, sub_id: UUID) -> bool:
        result = await self.session.execute(
            select(WebhookSubscription).where(WebhookSubscription.id == sub_id)
        )
        existing = result.scalar_one_or_none()
        if existing is None:
            return False
        await self.session.execute(
            sa_delete(WebhookSubscription).where(WebhookSubscription.id == sub_id)
        )
        return True

    async def list_deliveries(
        self, subscription_id: str | None = None, status: str | None = None,
        limit: int = 50, cursor: str | None = None,
    ) -> dict:
        stmt = select(WebhookDelivery)
        if subscription_id:
            stmt = stmt.where(WebhookDelivery.subscription_id == subscription_id)
        if status:
            stmt = stmt.where(WebhookDelivery.status == status)
        return await self.paginate(stmt, WebhookDelivery, limit=limit, cursor=cursor)

    async def emit_domain_event(
        self, event_type: str, aggregate_type: str, aggregate_id: UUID, payload: dict,
        cluster_id: UUID | None = None, principal_id: UUID | None = None,
    ) -> DomainEvent:
        event = DomainEvent()
        event.event_type = event_type
        event.aggregate_type = aggregate_type
        event.aggregate_id = aggregate_id
        event.payload = payload
        event.cluster_id = cluster_id
        event.principal_id = principal_id
        self.session.add(event)
        await self.session.flush()
        return event
