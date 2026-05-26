"""Feature flag evaluation with in-memory cache."""
from __future__ import annotations

import time
from uuid import UUID

from sqlalchemy import case, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from pinky_api.models.feature_flag import FeatureFlag

_CACHE_TTL = 30
_MAX_CACHE_SIZE = 10_000
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

    scope_filters = [FeatureFlag.scope_type == "global"]
    if principal_id:
        scope_filters.append(
            (FeatureFlag.scope_type == "principal") & (FeatureFlag.scope_id == principal_id)
        )
    if cluster_id:
        scope_filters.append(
            (FeatureFlag.scope_type == "cluster") & (FeatureFlag.scope_id == cluster_id)
        )

    stmt = (
        select(FeatureFlag)
        .where(FeatureFlag.flag_name == flag_name)
        .where(or_(*scope_filters))
        .order_by(
            case(
                (FeatureFlag.scope_type == "principal", 1),
                (FeatureFlag.scope_type == "cluster", 2),
                else_=3,
            )
        )
        .limit(1)
    )
    result = await db.execute(stmt)
    flag = result.scalar_one_or_none()
    enabled = flag.enabled if flag is not None else False

    if len(_cache) >= _MAX_CACHE_SIZE:
        oldest_key = min(_cache, key=lambda k: _cache[k][0])
        del _cache[oldest_key]

    _cache[cache_key] = (now, enabled)
    return enabled


def clear_cache() -> None:
    """Clear the cache. Used by tests and after flag updates."""
    _cache.clear()
