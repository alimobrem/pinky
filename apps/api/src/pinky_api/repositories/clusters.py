"""Cluster registry repository."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select

from pinky_api.models.fleet import ClusterRegistry
from pinky_api.repositories.base import BaseRepository


class ClusterRepository(BaseRepository):
    async def list(self, limit: int = 50, cursor: str | None = None) -> dict:
        stmt = select(ClusterRegistry)
        return await self.paginate(stmt, ClusterRegistry, limit=limit, cursor=cursor)

    async def list_all(self) -> list[ClusterRegistry]:
        result = await self.session.execute(select(ClusterRegistry))
        return list(result.scalars().all())

    async def get(self, cluster_id: UUID) -> ClusterRegistry | None:
        result = await self.session.execute(
            select(ClusterRegistry).where(ClusterRegistry.id == cluster_id)
        )
        return result.scalar_one_or_none()

    async def count(self) -> int:
        result = await self.session.execute(select(func.count(ClusterRegistry.id)))
        return result.scalar_one()

    async def create(self, **kwargs: object) -> ClusterRegistry:
        cluster = ClusterRegistry(**kwargs)
        self.session.add(cluster)
        await self.session.flush()
        return cluster

    async def delete(self, cluster_id: UUID) -> bool:
        cluster = await self.get(cluster_id)
        if cluster is None:
            return False
        cluster.offboarding_state = "offboarded"
        cluster.onboarding_state = "offboarded"
        await self.session.flush()
        return True
