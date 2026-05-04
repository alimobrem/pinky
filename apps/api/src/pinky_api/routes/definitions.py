"""Definition CRUD routes — manage scanners, tools, skills, policies via API."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from pinky_api.auth.deps import require_admin
from pinky_api.db.deps import get_db
from pinky_api.repositories.definitions_repo import DefinitionRepository

router = APIRouter(prefix="/api/v1/definitions", tags=["definitions"])


class DefinitionCreateRequest(BaseModel):
    kind: str
    name: str
    version: str = "1.0.0"
    frontmatter: dict
    body: str
    enabled: bool = True


def _serialize(d: Any) -> dict:
    return {
        "id": str(d.id),
        "kind": d.kind,
        "name": d.name,
        "version": d.version,
        "frontmatter": d.frontmatter,
        "body": d.body,
        "enabled": d.enabled,
        "created_at": d.created_at.isoformat() if d.created_at else "",
    }


@router.get("")
async def list_definitions(kind: str | None = None, db: AsyncSession = Depends(get_db)) -> dict:
    repo = DefinitionRepository(db)
    result = await repo.list(kind=kind)
    return {
        "items": [_serialize(d) for d in result["items"]],
        "next_cursor": result["next_cursor"],
        "has_more": result["has_more"],
    }


@router.get("/{kind}/{name}")
async def get_definition(kind: str, name: str, db: AsyncSession = Depends(get_db)) -> dict:
    repo = DefinitionRepository(db)
    d = await repo.get(kind, name)
    if d is None:
        raise HTTPException(status_code=404, detail="Definition not found")
    return _serialize(d)


@router.post("", status_code=201)
async def create_definition(
    req: DefinitionCreateRequest, db: AsyncSession = Depends(get_db), _admin: dict = Depends(require_admin),
) -> dict:
    repo = DefinitionRepository(db)
    d = await repo.upsert(
        kind=req.kind, name=req.name, version=req.version, frontmatter=req.frontmatter, body=req.body,
    )
    await db.commit()
    return _serialize(d)


@router.delete("/{kind}/{name}", status_code=204)
async def delete_definition(
    kind: str, name: str, db: AsyncSession = Depends(get_db), _admin: dict = Depends(require_admin),
) -> None:
    repo = DefinitionRepository(db)
    deleted = await repo.delete(kind, name)
    if not deleted:
        raise HTTPException(status_code=404, detail="Definition not found")
    await db.commit()
