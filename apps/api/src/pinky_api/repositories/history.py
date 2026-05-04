"""History repository — append-only audit events."""

from __future__ import annotations

from sqlalchemy import select

from pinky_api.models.history import HistoryEvent
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
        stmt = select(HistoryEvent)

        if cluster_id:
            stmt = stmt.where(HistoryEvent.cluster_id == cluster_id)
        if aggregate_type:
            stmt = stmt.where(HistoryEvent.aggregate_type == aggregate_type)
        if event_type:
            stmt = stmt.where(HistoryEvent.event_type == event_type)

        return await self.paginate(stmt, HistoryEvent, limit=limit, cursor=cursor, order_column="occurred_at")

    async def append(self, **kwargs: object) -> HistoryEvent:
        event = HistoryEvent(**kwargs)
        self.session.add(event)
        await self.session.flush()
        return event
