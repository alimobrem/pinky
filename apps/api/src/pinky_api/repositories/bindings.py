"""Cluster identity binding repository."""

from __future__ import annotations

from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy import update as sa_update

from pinky_api.models.fleet import ClusterIdentityBinding
from pinky_api.repositories.base import BaseRepository


class BindingRepository(BaseRepository):
    async def list_for_principal(self, principal_id: UUID) -> list[ClusterIdentityBinding]:
        result = await self.session.execute(
            select(ClusterIdentityBinding).where(ClusterIdentityBinding.principal_id == principal_id)
        )
        return list(result.scalars().all())

    async def get(self, binding_id: UUID) -> ClusterIdentityBinding | None:
        result = await self.session.execute(
            select(ClusterIdentityBinding).where(ClusterIdentityBinding.id == binding_id)
        )
        return result.scalar_one_or_none()

    async def get_for_cluster(self, principal_id: UUID, cluster_id: UUID) -> ClusterIdentityBinding | None:
        result = await self.session.execute(
            select(ClusterIdentityBinding).where(
                ClusterIdentityBinding.principal_id == principal_id,
                ClusterIdentityBinding.cluster_id == cluster_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_accessible_cluster_ids(self, principal_id: UUID) -> list[UUID]:
        result = await self.session.execute(
            select(ClusterIdentityBinding.cluster_id).where(
                ClusterIdentityBinding.principal_id == principal_id,
                ClusterIdentityBinding.status.in_(["valid", "expiring"]),
            )
        )
        return [row[0] for row in result.all()]

    async def create(self, **kwargs: object) -> ClusterIdentityBinding:
        binding = ClusterIdentityBinding(**kwargs)
        self.session.add(binding)
        await self.session.flush()
        return binding

    async def refresh(self, binding_id: UUID) -> ClusterIdentityBinding | None:
        result = await self.session.execute(
            sa_update(ClusterIdentityBinding)
            .where(ClusterIdentityBinding.id == binding_id)
            .values(status="valid", expires_at=datetime.utcnow() + timedelta(hours=8))
            .returning(ClusterIdentityBinding)
        )
        return result.scalar_one_or_none()

    async def refresh_token(
        self, binding_id: UUID, encrypted_token: bytes,
    ) -> ClusterIdentityBinding | None:
        result = await self.session.execute(
            sa_update(ClusterIdentityBinding)
            .where(ClusterIdentityBinding.id == binding_id)
            .values(
                status="valid",
                encrypted_token=encrypted_token,
                expires_at=datetime.utcnow() + timedelta(hours=8),
            )
            .returning(ClusterIdentityBinding)
        )
        return result.scalar_one_or_none()

    async def revoke(self, binding_id: UUID) -> bool:
        binding = await self.get(binding_id)
        if binding is None:
            return False
        await self.session.execute(
            sa_update(ClusterIdentityBinding)
            .where(ClusterIdentityBinding.id == binding_id)
            .values(status="revoked")
        )
        return True
