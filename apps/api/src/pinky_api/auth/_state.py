"""Mutable auth state — initialized in app lifespan."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pinky_api.auth.session_store import SessionStore

session_store: SessionStore | None = None
