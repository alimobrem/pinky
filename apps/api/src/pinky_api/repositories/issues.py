"""Issue repository — correlated operational problems."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy import update as sa_update

from pinky_api.models.issue import Issue
from pinky_api.repositories.base import BaseRepository


class IssueRepository(BaseRepository):
    async def list(
        self,
        cluster_id: str | None = None,
        cluster_ids: list[UUID] | None = None,
        status: str | None = None,
        severity: str | None = None,
        limit: int = 50,
        cursor: str | None = None,
    ) -> dict:
        stmt = select(Issue)

        if cluster_id:
            stmt = stmt.where(Issue.cluster_id == cluster_id)
        elif cluster_ids is not None:
            if not cluster_ids:
                return {"items": [], "next_cursor": None, "has_more": False}
            stmt = stmt.where(Issue.cluster_id.in_(cluster_ids))
        if status:
            stmt = stmt.where(Issue.status == status)
        if severity:
            stmt = stmt.where(Issue.severity == severity)

        return await self.paginate(stmt, Issue, limit=limit, cursor=cursor)

    async def get(self, issue_id: UUID) -> Issue | None:
        result = await self.session.execute(
            select(Issue).where(Issue.id == issue_id)
        )
        return result.scalar_one_or_none()

    async def suppress(self, issue_id: UUID, until: datetime | None = None) -> Issue | None:
        issue = await self.get(issue_id)
        if issue is None:
            return None
        values: dict = {"status": "suppressed"}
        if until:
            values["suppressed_until"] = until
        await self.session.execute(
            sa_update(Issue).where(Issue.id == issue_id).values(**values)
        )
        self.session.expire_all()
        return await self.get(issue_id)

    async def resolve(self, issue_id: UUID) -> Issue | None:
        issue = await self.get(issue_id)
        if issue is None:
            return None
        await self.session.execute(
            sa_update(Issue).where(Issue.id == issue_id).values(
                status="resolved",
                resolved_at=datetime.utcnow(),
            )
        )
        self.session.expire_all()
        return await self.get(issue_id)

    async def find_by_correlation_key(self, correlation_key: str) -> Issue | None:
        result = await self.session.execute(
            select(Issue).where(Issue.correlation_key == correlation_key, Issue.status == "open")
        )
        return result.scalar_one_or_none()
