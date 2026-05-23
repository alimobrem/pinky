"""Feature flag evaluation with in-memory cache."""
from __future__ import annotations

import time
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from pinky_api.models.feature_flag import FeatureFlag

_CACHE_TTL = 30
_cache: dict[str, tuple[float, bool]] = {}


async def is_enabled(
    db: AsyncSession,
    flag_name: str,
    principal_id: UUID | None = None,
    cluster_id: UUID | None = None,
) -> bool:
    """Check if a feature flag is enabled.

    Checks in order: principal scope -> cluster scope -> global scope.
    Caches results for 30 seconds to reduce DB load.
    """
    cache_key = f"{flag_name}:{principal_id}:{cluster_id}"
    now = time.monotonic()

    if cache_key in _cache:
        cached_at, value = _cache[cache_key]
        if now - cached_at < _CACHE_TTL:
            return value

    for scope_type, scope_id in [
        ("principal", principal_id),
        ("cluster", cluster_id),
        ("global", None),
    ]:
        if scope_type != "global" and scope_id is None:
            continue

        stmt = select(FeatureFlag).where(
            FeatureFlag.flag_name == flag_name, FeatureFlag.scope_type == scope_type
        )
        stmt = (
            stmt.where(FeatureFlag.scope_id == scope_id)
            if scope_id
            else stmt.where(FeatureFlag.scope_id.is_(None))
        )

        result = await db.execute(stmt)
        flag = result.scalar_one_or_none()
        if flag is not None:
            _cache[cache_key] = (now, flag.enabled)
            return flag.enabled

    _cache[cache_key] = (now, False)
    return False


def clear_cache() -> None:
    """Clear the cache. Used by tests and after flag updates."""
    _cache.clear()
