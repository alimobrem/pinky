"""Tests for worker database pool singleton."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from pinky_worker.db import close_pool, get_pool


class TestDbPool:
    @pytest.fixture(autouse=True)
    async def _reset_pool(self) -> None:
        from pinky_worker import db
        db._pool = None
        yield
        db._pool = None

    @pytest.mark.asyncio
    async def test_creates_pool_on_first_call(self) -> None:
        mock_pool = AsyncMock()
        with patch("pinky_worker.db.asyncpg.create_pool", AsyncMock(return_value=mock_pool)) as mock_create:
            pool = await get_pool()

        assert pool is mock_pool
        mock_create.assert_called_once()

    @pytest.mark.asyncio
    async def test_returns_same_pool_on_second_call(self) -> None:
        mock_pool = AsyncMock()
        with patch("pinky_worker.db.asyncpg.create_pool", AsyncMock(return_value=mock_pool)) as mock_create:
            p1 = await get_pool()
            p2 = await get_pool()

        assert p1 is p2
        mock_create.assert_called_once()

    @pytest.mark.asyncio
    async def test_uses_env_vars_for_config(self) -> None:
        mock_pool = AsyncMock()
        env = {
            "PINKY_DATABASE_URL": "postgresql://custom:pass@db:5432/mydb",
            "PINKY_DB_POOL_MIN": "2",
            "PINKY_DB_POOL_MAX": "10",
        }
        with (
            patch.dict("os.environ", env),
            patch("pinky_worker.db.asyncpg.create_pool", AsyncMock(return_value=mock_pool)) as mock_create,
        ):
            await get_pool()

        mock_create.assert_called_once_with(
            "postgresql://custom:pass@db:5432/mydb",
            min_size=2,
            max_size=10,
        )

    @pytest.mark.asyncio
    async def test_close_pool_closes_and_resets(self) -> None:
        mock_pool = AsyncMock()
        with patch("pinky_worker.db.asyncpg.create_pool", AsyncMock(return_value=mock_pool)):
            await get_pool()

        await close_pool()
        mock_pool.close.assert_called_once()

        from pinky_worker import db
        assert db._pool is None

    @pytest.mark.asyncio
    async def test_close_pool_noop_when_no_pool(self) -> None:
        await close_pool()
