"""Base repository with common pagination and filtering patterns."""

from __future__ import annotations

import base64
import json
from typing import Any, TypeVar
from uuid import UUID

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

        if cursor:
            cursor_data = decode_cursor(cursor)
            cursor_value = cursor_data.get("v")
            stmt = stmt.where(order_col < cursor_value)

        stmt = stmt.order_by(order_col.desc()).limit(limit + 1)

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
        }
