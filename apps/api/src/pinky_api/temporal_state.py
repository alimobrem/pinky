"""Temporal client state — lazy connection with retry."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from temporalio.client import Client

logger = logging.getLogger(__name__)

_client: Client | None = None
_connect_attempted: bool = False


async def get_client() -> Client:
    global _client, _connect_attempted

    if _client is not None:
        return _client

    from temporalio.client import Client as TemporalClient

    from pinky_api.config import get_settings

    settings = get_settings()
    _client = await TemporalClient.connect(
        settings.temporal.address,
        namespace=settings.temporal.namespace,
    )
    logger.info("Temporal connected: %s/%s", settings.temporal.address, settings.temporal.namespace)
    return _client
