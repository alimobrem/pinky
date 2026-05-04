"""Analytics repository — event recording and ROI queries."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select

from pinky_api.models.analytics import AnalyticsEvent
from pinky_api.repositories.base import BaseRepository


class AnalyticsRepository(BaseRepository):
    async def record(self, event_type: str, payload: dict, **kwargs: object) -> AnalyticsEvent:
        event = AnalyticsEvent(
            event_type=event_type,
            payload=payload,
            occurred_at=datetime.now(UTC),
            **kwargs,
        )
        self.session.add(event)
        await self.session.flush()
        return event

    async def list_by_type(
        self,
        event_type: str,
        limit: int = 100,
        cursor: str | None = None,
    ) -> dict:
        stmt = select(AnalyticsEvent).where(AnalyticsEvent.event_type == event_type)
        return await self.paginate(stmt, AnalyticsEvent, limit=limit, cursor=cursor, order_column="occurred_at")
