"""Issue repository — correlated operational problems."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select

from pinky_api.models.issue import Issue
from pinky_api.repositories.base import BaseRepository


class IssueRepository(BaseRepository):
    async def list(
        self,
        cluster_id: str | None = None,
        status: str | None = None,
        severity: str | None = None,
        limit: int = 50,
        cursor: str | None = None,
    ) -> dict:
        stmt = select(Issue)

        if cluster_id:
            stmt = stmt.where(Issue.cluster_id == cluster_id)
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

    async def find_by_correlation_key(self, correlation_key: str) -> Issue | None:
        result = await self.session.execute(
            select(Issue).where(Issue.correlation_key == correlation_key, Issue.status == "open")
        )
        return result.scalar_one_or_none()
