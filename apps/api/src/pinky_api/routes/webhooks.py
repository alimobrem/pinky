"""Webhook subscription routes — outbound notification management."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from pinky_api.auth.deps import require_admin

router = APIRouter(prefix="/api/v1", tags=["webhooks"])


class WebhookCreateRequest(BaseModel):
    name: str
    url: str
    event_patterns: list[str]
    formatter: str = "generic"
    channel_config: dict = {}


@router.get("/webhook-subscriptions")
async def list_webhook_subscriptions() -> dict:
    return {"items": [], "next_cursor": None, "has_more": False}


@router.post("/webhook-subscriptions", status_code=201)
async def create_webhook_subscription(req: WebhookCreateRequest, _admin: dict = Depends(require_admin)) -> dict:
    return {"message": "Webhook creation not yet implemented"}


@router.delete("/webhook-subscriptions/{subscription_id}", status_code=204)
async def delete_webhook_subscription(subscription_id: str, _admin: dict = Depends(require_admin)) -> None:
    pass


@router.get("/webhook-deliveries")
async def list_webhook_deliveries(
    subscription_id: str | None = None,
    status: str | None = None,
    limit: int = 50,
) -> dict:
    return {"items": [], "next_cursor": None, "has_more": False}
