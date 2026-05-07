"""API token CRUD routes — create, list, and revoke tokens for CLI/CI auth."""

import secrets
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from pinky_api.auth.deps import require_authenticated
from pinky_api.db.deps import get_db
from pinky_api.models.extensibility import ApiToken
from pinky_api.security.crypto import hash_token

router = APIRouter(prefix="/api/v1/api-tokens", tags=["api-tokens"])


class TokenCreateRequest(BaseModel):
    name: str
    scopes: list[str] = []
    expires_at: str | None = None


def _serialize(t: ApiToken) -> dict:
    return {
        "id": str(t.id),
        "name": t.name,
        "scopes": list(t.scopes) if t.scopes else [],
        "last_used_at": t.last_used_at.isoformat() if t.last_used_at else None,
        "expires_at": t.expires_at.isoformat() if t.expires_at else None,
        "created_at": t.created_at.isoformat() if t.created_at else "",
    }


@router.post("", status_code=201)
async def create_api_token(
    req: TokenCreateRequest,
    principal: dict = Depends(require_authenticated),
    db: AsyncSession = Depends(get_db),
) -> dict:
    raw_token = secrets.token_urlsafe(32)
    token_hash_value = hash_token(raw_token)

    expires_at = None
    if req.expires_at:
        parsed = datetime.fromisoformat(req.expires_at)
        expires_at = parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)

    token = ApiToken(
        principal_id=principal["id"],
        token_hash=token_hash_value,
        name=req.name,
        scopes=req.scopes,
        expires_at=expires_at,
    )
    db.add(token)
    await db.commit()
    await db.refresh(token)

    result = _serialize(token)
    result["token"] = raw_token
    return result


@router.get("")
async def list_api_tokens(
    principal: dict = Depends(require_authenticated),
    db: AsyncSession = Depends(get_db),
) -> dict:
    stmt = (
        select(ApiToken)
        .where(ApiToken.principal_id == principal["id"])
        .where(ApiToken.revoked_at.is_(None))
        .order_by(ApiToken.created_at.desc())
    )
    result = await db.execute(stmt)
    tokens = result.scalars().all()
    return {"items": [_serialize(t) for t in tokens]}


@router.delete("/{token_id}", status_code=204)
async def revoke_api_token(
    token_id: str,
    principal: dict = Depends(require_authenticated),
    db: AsyncSession = Depends(get_db),
) -> None:
    stmt = select(ApiToken).where(ApiToken.id == token_id)
    result = await db.execute(stmt)
    token = result.scalar_one_or_none()

    if token is None:
        raise HTTPException(status_code=404, detail="API token not found")

    # Only owner or admin can revoke
    if str(token.principal_id) != principal["id"] and not principal.get("is_admin"):
        raise HTTPException(status_code=403, detail="Not authorized to revoke this token")

    if token.revoked_at is not None:
        raise HTTPException(status_code=404, detail="API token already revoked")

    await db.execute(
        update(ApiToken)
        .where(ApiToken.id == token_id)
        .values(revoked_at=datetime.now(UTC))
    )
    await db.commit()
