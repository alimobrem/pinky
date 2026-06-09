"""Policy rule repository."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import delete as sa_delete
from sqlalchemy import select

from pinky_api.models.extensibility import PolicyRule
from pinky_api.repositories.base import BaseRepository


class PolicyRuleRepository(BaseRepository):
    async def list(self, limit: int = 50, cursor: str | None = None) -> dict:
        stmt = select(PolicyRule).order_by(PolicyRule.priority)
        return await self.paginate(stmt, PolicyRule, limit=limit, cursor=cursor)

    async def get(self, rule_id: UUID) -> PolicyRule | None:
        result = await self.session.execute(select(PolicyRule).where(PolicyRule.id == rule_id))
        return result.scalar_one_or_none()

    async def create(self, **kwargs: object) -> PolicyRule:
        rule = PolicyRule(**kwargs)
        self.session.add(rule)
        await self.session.flush()
        return rule

    async def list_enabled(self) -> list[PolicyRule]:
        """Return all enabled rules ordered by priority (for evaluation)."""
        stmt = select(PolicyRule).where(PolicyRule.enabled.is_(True)).order_by(PolicyRule.priority)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def delete(self, rule_id: UUID) -> bool:
        existing = await self.get(rule_id)
        if existing is None:
            return False
        await self.session.execute(sa_delete(PolicyRule).where(PolicyRule.id == rule_id))
        return True
