"""Base repository with common pagination and filtering patterns."""

from __future__ import annotations

import base64
import json
from datetime import datetime
from typing import TypeVar

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

T = TypeVar("T")

DEFAULT_LIMIT = 50
MAX_LIMIT = 200


def clamp_limit(limit: int) -> int:
    return max(1, min(limit, MAX_LIMIT))


def encode_cursor(data: dict) -> str:
    return base64.urlsafe_b64encode(json.dumps(data).encode()).decode()


def decode_cursor(cursor: str) -> dict:
    return json.loads(base64.urlsafe_b64decode(cursor.encode()).decode())


DATETIME_CURSOR_COLUMNS = {
    "created_at",
    "updated_at",
    "occurred_at",
    "observed_at",
    "started_at",
    "completed_at",
    "expires_at",
    "first_seen_at",
    "last_seen_at",
}


class BaseRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def paginate(
        self,
        stmt: Select,
        model_class: type,
        limit: int = DEFAULT_LIMIT,
        cursor: str | None = None,
        order_column: str = "created_at",
    ) -> dict:
        limit = clamp_limit(limit)
        order_col = getattr(model_class, order_column)
        count_stmt = select(func.count()).select_from(stmt.order_by(None).subquery())

        if cursor:
            cursor_data = decode_cursor(cursor)
            cursor_value = cursor_data.get("v")
            if isinstance(cursor_value, str) and order_column in DATETIME_CURSOR_COLUMNS:
                cursor_value = datetime.fromisoformat(cursor_value)
            stmt = stmt.where(order_col < cursor_value)

        stmt = stmt.order_by(order_col.desc()).limit(limit + 1)

        total_result = await self.session.execute(count_stmt)
        total_count = int(total_result.scalar_one() or 0)
        result = await self.session.execute(stmt)
        rows = result.scalars().all()

        has_more = len(rows) > limit
        items = rows[:limit]

        next_cursor = None
        if has_more and items:
            last = items[-1]
            val = getattr(last, order_column)
            next_cursor = encode_cursor({"v": val.isoformat() if hasattr(val, "isoformat") else str(val)})

        return {
            "items": items,
            "next_cursor": next_cursor,
            "has_more": has_more,
            "total_count": total_count,
        }
