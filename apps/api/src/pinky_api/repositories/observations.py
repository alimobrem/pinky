"""Observation repository — raw scanner signals."""

from sqlalchemy import select

from pinky_api.models.observation import Observation
from pinky_api.repositories.base import BaseRepository


class ObservationRepository(BaseRepository):
    async def list(
        self, cluster_id: str | None = None, cluster_ids: list | None = None,
        severity: str | None = None, limit: int = 50, cursor: str | None = None,
    ) -> dict:
        stmt = select(Observation)
        if cluster_id:
            stmt = stmt.where(Observation.cluster_id == cluster_id)
        elif cluster_ids is not None:
            if not cluster_ids:
                return {"items": [], "next_cursor": None, "has_more": False}
            stmt = stmt.where(Observation.cluster_id.in_(cluster_ids))
        if severity:
            stmt = stmt.where(Observation.severity == severity)
        return await self.paginate(stmt, Observation, limit=limit, cursor=cursor, order_column="observed_at")
