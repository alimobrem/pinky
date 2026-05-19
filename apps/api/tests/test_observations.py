"""Observation repository unit tests — filter logic and edge cases."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from pinky_api.repositories.observations import ObservationRepository


@pytest.fixture
def mock_session() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def repo(mock_session: AsyncMock) -> ObservationRepository:
    return ObservationRepository(mock_session)


@pytest.mark.asyncio
async def test_list_empty_cluster_ids_returns_empty(repo: ObservationRepository) -> None:
    result = await repo.list(cluster_ids=[])
    assert result == {"items": [], "next_cursor": None, "has_more": False}


@pytest.mark.asyncio
async def test_list_empty_cluster_ids_skips_db(
    repo: ObservationRepository, mock_session: AsyncMock,
) -> None:
    await repo.list(cluster_ids=[])
    mock_session.execute.assert_not_called()
