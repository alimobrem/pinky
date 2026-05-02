"""Definition CRUD routes — manage scanners, tools, skills, policies via API."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

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
    # TODO: query definitions table + merge filesystem definitions
    return {"items": [], "next_cursor": None, "has_more": False}


@router.get("/{kind}/{name}")
async def get_definition(kind: str, name: str) -> dict:
    # TODO: look up by (kind, name), DB overrides filesystem
    raise HTTPException(status_code=404, detail="Definition not found")


@router.post("", status_code=201)
async def create_definition(req: DefinitionCreateRequest) -> dict:
    # TODO: check_product_authz(principal, Role.ADMIN)
    # TODO: upsert into definitions table
    # TODO: emit domain event definition.created
    return {"message": "Definition creation not yet implemented"}


@router.delete("/{kind}/{name}", status_code=204)
async def delete_definition(kind: str, name: str) -> None:
    # TODO: check_product_authz(principal, Role.ADMIN)
    # TODO: delete from definitions table (filesystem defs can't be deleted via API)
    pass
