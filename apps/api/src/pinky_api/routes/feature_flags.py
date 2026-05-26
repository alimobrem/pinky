"""Feature flag CRUD routes — admin only."""
from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from pinky_api.auth.deps import require_admin
from pinky_api.db.deps import get_db
from pinky_api.models.feature_flag import FeatureFlag
from pinky_api.services import feature_flags as ff_service

router = APIRouter(prefix="/api/v1/feature-flags", tags=["feature-flags"])


class CreateFlagRequest(BaseModel):
    flag_name: str
    enabled: bool = False
    scope_type: str = "global"
    scope_id: str | None = None


class UpdateFlagRequest(BaseModel):
    enabled: bool | None = None
    scope_type: str | None = None
    scope_id: str | None = None


def _serialize(flag: FeatureFlag) -> dict:
    return {
        "id": str(flag.id),
        "flag_name": flag.flag_name,
        "enabled": flag.enabled,
        "scope_type": flag.scope_type,
        "scope_id": str(flag.scope_id) if flag.scope_id else None,
        "created_at": flag.created_at.isoformat() if flag.created_at else "",
        "updated_at": flag.updated_at.isoformat() if flag.updated_at else "",
    }


@router.post("", status_code=201)
async def create_flag(
    body: CreateFlagRequest,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(require_admin),
) -> dict:
    flag = FeatureFlag(
        flag_name=body.flag_name,
        enabled=body.enabled,
        scope_type=body.scope_type,
        scope_id=UUID(body.scope_id) if body.scope_id else None,
    )
    db.add(flag)
    await db.commit()
    await db.refresh(flag)
    ff_service.clear_cache()
    return _serialize(flag)


@router.get("")
async def list_flags(
    db: AsyncSession = Depends(get_db), _: dict = Depends(require_admin)
) -> dict:
    result = await db.execute(select(FeatureFlag).order_by(FeatureFlag.flag_name))
    flags = result.scalars().all()
    return {"flags": [_serialize(f) for f in flags]}


@router.patch("/{flag_id}")
async def update_flag(
    flag_id: str,
    body: UpdateFlagRequest,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(require_admin),
) -> dict:
    result = await db.execute(select(FeatureFlag).where(FeatureFlag.id == UUID(flag_id)))
    flag = result.scalar_one_or_none()
    if not flag:
        raise HTTPException(status_code=404, detail="Flag not found")

    if body.enabled is not None:
        flag.enabled = body.enabled
    if body.scope_type is not None:
        flag.scope_type = body.scope_type
    if body.scope_id is not None:
        flag.scope_id = UUID(body.scope_id)

    flag.updated_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(flag)
    ff_service.clear_cache()
    return _serialize(flag)


@router.delete("/{flag_id}", status_code=204)
async def delete_flag(
    flag_id: str,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(require_admin),
) -> None:
    result = await db.execute(select(FeatureFlag).where(FeatureFlag.id == UUID(flag_id)))
    flag = result.scalar_one_or_none()
    if not flag:
        raise HTTPException(status_code=404, detail="Flag not found")

    await db.delete(flag)
    await db.commit()
    ff_service.clear_cache()
