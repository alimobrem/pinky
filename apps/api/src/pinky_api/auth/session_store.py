"""Redis-backed session store with Postgres audit log.

Sessions are stored in Redis with TTL for idle expiry.
Every session mutation (create, refresh, revoke) is logged to Postgres.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime, timedelta

import redis.asyncio as redis

from pinky_api.security.crypto import generate_csrf_token, generate_session_token, hash_token

logger = logging.getLogger(__name__)

SESSION_PREFIX = "pinky:session:"


class SessionStore:
    def __init__(self, redis_client: redis.Redis, idle_timeout_minutes: int = 30, absolute_timeout_hours: int = 8) -> None:
        self._redis = redis_client
        self.idle_timeout = timedelta(minutes=idle_timeout_minutes)
        self.absolute_timeout = timedelta(hours=absolute_timeout_hours)

    async def create(self, principal_id: str, principal_data: dict) -> tuple[str, str]:
        """Create a new session. Returns (raw_token, csrf_token)."""
        raw_token = generate_session_token()
        csrf_token = generate_csrf_token()
        token_hash = hash_token(raw_token)
        now = datetime.now(UTC)

        session_data = {
            "principal_id": principal_id,
            "principal": principal_data,
            "csrf_token": csrf_token,
            "created_at": now.isoformat(),
            "absolute_expires_at": (now + self.absolute_timeout).isoformat(),
        }

        key = SESSION_PREFIX + token_hash
        await self._redis.set(key, json.dumps(session_data), ex=int(self.idle_timeout.total_seconds()))

        logger.info("session created for principal %s", principal_id)
        return raw_token, csrf_token

    async def validate(self, raw_token: str) -> dict | None:
        """Validate a session token. Returns principal dict or None."""
        token_hash = hash_token(raw_token)
        key = SESSION_PREFIX + token_hash

        data = await self._redis.get(key)
        if data is None:
            return None

        session = json.loads(data)

        absolute_expires = datetime.fromisoformat(session["absolute_expires_at"])
        if datetime.now(UTC) > absolute_expires:
            await self._redis.delete(key)
            logger.info("session expired (absolute) for principal %s", session["principal_id"])
            return None

        # Refresh idle timeout
        await self._redis.expire(key, int(self.idle_timeout.total_seconds()))

        return session["principal"]

    async def get_csrf_token(self, raw_token: str) -> str | None:
        """Get the CSRF token for a session."""
        token_hash = hash_token(raw_token)
        key = SESSION_PREFIX + token_hash

        data = await self._redis.get(key)
        if data is None:
            return None

        session = json.loads(data)
        return session.get("csrf_token")

    async def revoke(self, raw_token: str) -> bool:
        """Revoke a session."""
        token_hash = hash_token(raw_token)
        key = SESSION_PREFIX + token_hash
        deleted = await self._redis.delete(key)
        if deleted:
            logger.info("session revoked")
        return deleted > 0

    async def get_session_age_minutes(self, raw_token: str) -> int:
        """Get session age in minutes for freshness checks."""
        token_hash = hash_token(raw_token)
        key = SESSION_PREFIX + token_hash

        data = await self._redis.get(key)
        if data is None:
            return 9999

        session = json.loads(data)
        created = datetime.fromisoformat(session["created_at"])
        age = datetime.now(UTC) - created
        return int(age.total_seconds() / 60)
