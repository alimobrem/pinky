"""Work item repository — task CRUD and lifecycle transitions."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select, update as sa_update

from pinky_api.models.work_item import WorkItem
from pinky_api.repositories.base import BaseRepository


VALID_TRANSITIONS: dict[str, set[str]] = {
    "ready": {"accepted"},
    "accepted": {"in_progress", "done"},
    "in_progress": {"blocked", "waiting_for_approval", "done"},
    "blocked": {"in_progress", "done"},
    "waiting_for_approval": {"in_progress"},
}


class WorkItemRepository(BaseRepository):
    async def list(
        self,
        cluster_id: str | None = None,
        status: str | None = None,
        owner_id: str | None = None,
        priority: str | None = None,
        limit: int = 50,
        cursor: str | None = None,
    ) -> dict:
        stmt = select(WorkItem)

        if cluster_id:
            stmt = stmt.where(WorkItem.cluster_id == cluster_id)
        if status:
            statuses = [s.strip() for s in status.split(",")]
            stmt = stmt.where(WorkItem.status.in_(statuses))
        if owner_id:
            stmt = stmt.where(WorkItem.owner_id == owner_id)
        if priority:
            stmt = stmt.where(WorkItem.priority == priority)

        return await self.paginate(stmt, WorkItem, limit=limit, cursor=cursor)

    async def get(self, work_item_id: UUID) -> WorkItem | None:
        result = await self.session.execute(
            select(WorkItem).where(WorkItem.id == work_item_id)
        )
        return result.scalar_one_or_none()

    async def transition(self, work_item_id: UUID, new_status: str, owner_id: UUID | None = None) -> WorkItem | None:
        item = await self.get(work_item_id)
        if item is None:
            return None

        allowed = VALID_TRANSITIONS.get(item.status, set())
        if new_status not in allowed:
            raise ValueError(f"Cannot transition from {item.status} to {new_status}")

        values: dict = {"status": new_status}
        if owner_id is not None:
            values["owner_id"] = owner_id

        await self.session.execute(
            sa_update(WorkItem).where(WorkItem.id == work_item_id).values(**values)
        )
        self.session.expire_all()
        return await self.get(work_item_id)

    async def reassign(self, work_item_id: UUID, new_owner_id: UUID) -> WorkItem | None:
        result = await self.session.execute(
            sa_update(WorkItem).where(WorkItem.id == work_item_id).values(owner_id=new_owner_id)
        )
        if result.rowcount == 0:
            return None
        return await self.get(work_item_id)

    async def create(self, **kwargs: object) -> WorkItem:
        item = WorkItem(**kwargs)
        self.session.add(item)
        await self.session.flush()
        return item
