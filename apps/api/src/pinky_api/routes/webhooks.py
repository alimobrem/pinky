"""Webhook subscription routes — outbound notification management."""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from pinky_api.auth.deps import require_admin
from pinky_api.db.deps import get_db
from pinky_api.repositories.webhooks import WebhookRepository

router = APIRouter(prefix="/api/v1", tags=["webhooks"])


class WebhookCreateRequest(BaseModel):
    name: str
    url: str
    event_patterns: list[str]
    formatter: str = "generic"
    channel_config: dict = {}


def _serialize_sub(s: Any) -> dict:
    return {
        "id": str(s.id),
        "name": s.name,
        "url": s.url,
        "event_patterns": list(s.event_patterns) if s.event_patterns else [],
        "formatter": s.formatter,
        "enabled": s.enabled,
        "created_at": s.created_at.isoformat() if s.created_at else "",
    }


def _serialize_delivery(d: Any) -> dict:
    return {
        "id": str(d.id),
        "subscription_id": str(d.subscription_id),
        "domain_event_id": str(d.domain_event_id),
        "status": d.status,
        "attempts": d.attempts,
        "last_attempt_at": d.last_attempt_at.isoformat() if d.last_attempt_at else None,
        "last_response_code": d.last_response_code,
        "next_retry_at": d.next_retry_at.isoformat() if d.next_retry_at else None,
        "created_at": d.created_at.isoformat() if d.created_at else "",
    }


@router.get("/webhook-subscriptions")
async def list_webhook_subscriptions(db: AsyncSession = Depends(get_db)) -> dict:
    repo = WebhookRepository(db)
    result = await repo.list_subscriptions()
    return {
        "items": [_serialize_sub(s) for s in result["items"]],
        "next_cursor": result["next_cursor"],
        "has_more": result["has_more"],
    }


@router.post("/webhook-subscriptions", status_code=201)
async def create_webhook_subscription(
    req: WebhookCreateRequest, db: AsyncSession = Depends(get_db), _admin: dict = Depends(require_admin),
) -> dict:
    repo = WebhookRepository(db)
    sub = await repo.create_subscription(
        name=req.name, url=req.url, event_patterns=req.event_patterns,
        formatter=req.formatter, channel_config=req.channel_config,
    )
    await db.commit()
    return _serialize_sub(sub)


@router.delete("/webhook-subscriptions/{subscription_id}", status_code=204)
async def delete_webhook_subscription(
    subscription_id: str, db: AsyncSession = Depends(get_db), _admin: dict = Depends(require_admin),
) -> None:
    repo = WebhookRepository(db)
    deleted = await repo.delete_subscription(UUID(subscription_id))
    if not deleted:
        raise HTTPException(status_code=404, detail="Subscription not found")
    await db.commit()


@router.get("/webhook-deliveries")
async def list_webhook_deliveries(
    subscription_id: str | None = None, status: str | None = None,
    limit: int = 50, db: AsyncSession = Depends(get_db),
) -> dict:
    repo = WebhookRepository(db)
    result = await repo.list_deliveries(subscription_id=subscription_id, status=status, limit=limit)
    return {
        "items": [_serialize_delivery(d) for d in result["items"]],
        "next_cursor": result["next_cursor"],
        "has_more": result["has_more"],
    }
