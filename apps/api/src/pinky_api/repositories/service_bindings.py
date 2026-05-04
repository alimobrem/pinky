"""Service binding repository — observer/read-only cluster integrations."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select

from pinky_api.models.extensibility import ServiceBinding
from pinky_api.repositories.base import BaseRepository


class ServiceBindingRepository(BaseRepository):
    async def list(self, cluster_id: str | None = None) -> list[ServiceBinding]:
        stmt = select(ServiceBinding)
        if cluster_id:
            stmt = stmt.where(ServiceBinding.cluster_id == cluster_id)
        result = await self.session.execute(stmt.order_by(ServiceBinding.created_at.desc()))
        return list(result.scalars().all())

    async def get(self, binding_id: UUID) -> ServiceBinding | None:
        result = await self.session.execute(
            select(ServiceBinding).where(ServiceBinding.id == binding_id)
        )
        return result.scalar_one_or_none()

    async def create(self, **kwargs: object) -> ServiceBinding:
        binding = ServiceBinding(**kwargs)
        self.session.add(binding)
        await self.session.flush()
        return binding

    async def delete(self, binding_id: UUID) -> bool:
        binding = await self.get(binding_id)
        if binding is None:
            return False
        await self.session.delete(binding)
        await self.session.flush()
        return True
