"""Execution repository."""

from uuid import UUID

from sqlalchemy import select

from pinky_api.models.execution import Approval, Execution
from pinky_api.repositories.base import BaseRepository


class ExecutionRepository(BaseRepository):
    async def list(self, work_item_id: str | None = None, cluster_id: str | None = None, status: str | None = None, limit: int = 50, cursor: str | None = None) -> dict:
        stmt = select(Execution)
        if work_item_id:
            stmt = stmt.where(Execution.work_item_id == work_item_id)
        if cluster_id:
            stmt = stmt.where(Execution.cluster_id == cluster_id)
        if status:
            stmt = stmt.where(Execution.status == status)
        return await self.paginate(stmt, Execution, limit=limit, cursor=cursor)

    async def get(self, execution_id: UUID) -> Execution | None:
        result = await self.session.execute(select(Execution).where(Execution.id == execution_id))
        return result.scalar_one_or_none()

    async def create(self, **kwargs: object) -> Execution:
        ex = Execution(**kwargs)
        self.session.add(ex)
        await self.session.flush()
        return ex
