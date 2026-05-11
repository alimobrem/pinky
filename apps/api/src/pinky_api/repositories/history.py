"""History repository — append-only audit events."""

from __future__ import annotations

from sqlalchemy import select

from pinky_api.models.extensibility import DomainEvent
from pinky_api.repositories.base import BaseRepository


class HistoryRepository(BaseRepository):
    async def list(
        self,
        cluster_id: str | None = None,
        aggregate_type: str | None = None,
        event_type: str | None = None,
        limit: int = 50,
        cursor: str | None = None,
    ) -> dict:
        stmt = select(DomainEvent)

        if cluster_id:
            stmt = stmt.where(DomainEvent.cluster_id == cluster_id)
        if aggregate_type:
            stmt = stmt.where(DomainEvent.aggregate_type == aggregate_type)
        if event_type:
            stmt = stmt.where(DomainEvent.event_type == event_type)

        return await self.paginate(stmt, DomainEvent, limit=limit, cursor=cursor, order_column="occurred_at")

    async def append(self, **kwargs: object) -> DomainEvent:
        event = DomainEvent(**kwargs)
        self.session.add(event)
        await self.session.flush()
        return event
