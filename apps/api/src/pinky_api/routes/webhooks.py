"""Webhook subscription routes — outbound notification management."""

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1", tags=["webhooks"])


class WebhookCreateRequest(BaseModel):
    name: str
    url: str
    event_patterns: list[str]
    formatter: str = "generic"
    channel_config: dict = {}


@router.get("/webhook-subscriptions")
async def list_webhook_subscriptions() -> dict:
    # TODO: query webhook_subscriptions table
    return {"items": [], "next_cursor": None, "has_more": False}


@router.post("/webhook-subscriptions", status_code=201)
async def create_webhook_subscription(req: WebhookCreateRequest) -> dict:
    # TODO: check_product_authz(principal, Role.ADMIN)
    # TODO: insert into webhook_subscriptions
    return {"message": "Webhook creation not yet implemented"}


@router.delete("/webhook-subscriptions/{subscription_id}", status_code=204)
async def delete_webhook_subscription(subscription_id: str) -> None:
    # TODO: check_product_authz(principal, Role.ADMIN)
    pass


@router.get("/webhook-deliveries")
async def list_webhook_deliveries(
    subscription_id: str | None = None,
    status: str | None = None,
    limit: int = 50,
) -> dict:
    # TODO: query webhook_deliveries for debugging
    return {"items": [], "next_cursor": None, "has_more": False}
