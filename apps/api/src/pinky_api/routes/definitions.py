"""Definition CRUD routes — manage scanners, tools, skills, policies via API."""

import logging
import os
from pathlib import Path
from typing import Any

import yaml
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from pinky_api.auth.deps import require_admin
from pinky_api.db.deps import get_db
from pinky_api.repositories.definitions_repo import DefinitionRepository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/definitions", tags=["definitions"])


class DefinitionCreateRequest(BaseModel):
    kind: str
    name: str
    version: str = "1.0.0"
    frontmatter: dict
    body: str
    enabled: bool = True


_KIND_DIRS = {
    "scanner": "scanners",
    "tool": "tools",
    "skill": "skills",
    "pipeline": "pipelines",
    "policy": "policies",
    "redaction-rule": "redaction-rules",
    "approval-policy": "approval-policies",
}


def _load_filesystem_definitions(definitions_dir: str) -> list[dict]:
    results: list[dict] = []
    base = Path(definitions_dir)
    if not base.exists():
        return results
    for kind, dirname in _KIND_DIRS.items():
        kind_dir = base / dirname
        if not kind_dir.is_dir():
            continue
        for md_file in sorted(kind_dir.glob("*.md")):
            try:
                text = md_file.read_text()
                if not text.startswith("---"):
                    continue
                end = text.index("---", 3)
                fm = yaml.safe_load(text[3:end])
                if not isinstance(fm, dict):
                    continue
                body = text[end + 3:].strip()
                name = fm.get("name", md_file.stem)
                results.append({
                    "id": f"fs-{name}",
                    "kind": fm.get("kind", kind),
                    "name": name,
                    "version": fm.get("version", "1.0.0"),
                    "enabled": fm.get("enabled", True),
                    "frontmatter": fm,
                    "body": body,
                    "source": "filesystem",
                    "created_at": None,
                    "updated_at": None,
                })
            except Exception:
                logger.exception("Failed to parse definition %s", md_file)
                continue
    return results


def _serialize(d: Any) -> dict:
    return {
        "id": str(d.id),
        "kind": d.kind,
        "name": d.name,
        "version": d.version,
        "frontmatter": d.frontmatter,
        "body": d.body,
        "enabled": d.enabled,
        "source": "database",
        "created_at": d.created_at.isoformat() if d.created_at else "",
        "updated_at": d.updated_at.isoformat() if d.updated_at else None,
    }


@router.get("")
async def list_definitions(kind: str | None = None, db: AsyncSession = Depends(get_db)) -> dict:
    repo = DefinitionRepository(db)
    result = await repo.list(kind=kind)
    db_items = [_serialize(d) for d in result["items"]]

    # Build set of (kind, name) from DB — DB overrides filesystem
    db_keys = {(d["kind"], d["name"]) for d in db_items}

    definitions_dir = os.environ.get(
        "PINKY_DEFINITIONS_DIR",
        str(Path(__file__).resolve().parent.parent.parent.parent.parent / "definitions"),
    )
    fs_defs = _load_filesystem_definitions(definitions_dir)
    fs_items = [d for d in fs_defs if (d["kind"], d["name"]) not in db_keys]

    # Apply kind filter to filesystem definitions
    if kind:
        fs_items = [d for d in fs_items if d["kind"] == kind]

    merged = db_items + fs_items
    return {
        "items": merged,
        "next_cursor": result["next_cursor"],
        "has_more": result["has_more"],
    }


@router.get("/{kind}/{name}")
async def get_definition(kind: str, name: str, db: AsyncSession = Depends(get_db)) -> dict:
    repo = DefinitionRepository(db)
    d = await repo.get(kind, name)
    if d is not None:
        return _serialize(d)

    # Fallback to filesystem
    definitions_dir = os.environ.get(
        "PINKY_DEFINITIONS_DIR",
        str(Path(__file__).resolve().parent.parent.parent.parent.parent / "definitions"),
    )
    for fs_def in _load_filesystem_definitions(definitions_dir):
        if fs_def["kind"] == kind and fs_def["name"] == name:
            return fs_def
    raise HTTPException(status_code=404, detail="Definition not found")


@router.post("", status_code=201)
async def create_definition(
    req: DefinitionCreateRequest, db: AsyncSession = Depends(get_db), _admin: dict = Depends(require_admin),
) -> dict:
    repo = DefinitionRepository(db)
    d = await repo.upsert(
        kind=req.kind, name=req.name, version=req.version, frontmatter=req.frontmatter, body=req.body,
    )
    await db.commit()
    await db.refresh(d)
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
