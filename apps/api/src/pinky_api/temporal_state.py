"""Temporal client state — initialized in app lifespan."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from temporalio.client import Client

client: Client | None = None
