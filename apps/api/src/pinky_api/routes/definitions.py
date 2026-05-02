"""Definition CRUD routes — manage scanners, tools, skills, policies via API."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from pinky_api.auth.deps import require_admin

router = APIRouter(prefix="/api/v1/definitions", tags=["definitions"])


class DefinitionCreateRequest(BaseModel):
    kind: str
    name: str
    version: str = "1.0.0"
    frontmatter: dict
    body: str
    enabled: bool = True


@router.get("")
async def list_definitions(kind: str | None = None) -> dict:
    return {"items": [], "next_cursor": None, "has_more": False}


@router.get("/{kind}/{name}")
async def get_definition(kind: str, name: str) -> dict:
    raise HTTPException(status_code=404, detail="Definition not found")


@router.post("", status_code=201)
async def create_definition(req: DefinitionCreateRequest, _admin: dict = Depends(require_admin)) -> dict:
    return {"message": "Definition creation not yet implemented"}


@router.delete("/{kind}/{name}", status_code=204)
async def delete_definition(kind: str, name: str, _admin: dict = Depends(require_admin)) -> None:
    pass
