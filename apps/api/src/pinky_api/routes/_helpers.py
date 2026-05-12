"""Shared helpers for route handlers."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from pinky_api.models.fleet import ClusterRegistry


async def resolve_cluster_names(items: list[dict], db: AsyncSession) -> None:
    """Batch-resolve cluster_id → display_name for serialized dicts."""
    cluster_ids = {UUID(i["cluster_id"]) for i in items if i.get("cluster_id")}
    if not cluster_ids:
        return
    rows = (await db.execute(
        select(ClusterRegistry.id, ClusterRegistry.display_name).where(
            ClusterRegistry.id.in_(cluster_ids)
        )
    )).all()
    name_map: dict[str, str] = {str(row[0]): row[1] for row in rows}
    for item in items:
        item["cluster_display_name"] = name_map.get(item.get("cluster_id", ""))
