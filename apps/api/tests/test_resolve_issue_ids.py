"""Tests for _resolve_issue_ids on execution list responses."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from pinky_api.routes.executions import _resolve_issue_ids


@pytest.fixture
def mock_db() -> AsyncMock:
    return AsyncMock()


@pytest.mark.asyncio
async def test_resolves_issue_ids_from_work_items(mock_db: AsyncMock) -> None:
    wi_id = uuid.uuid4()
    issue_id = uuid.uuid4()
    mock_db.execute.return_value = MagicMock(
        all=lambda: [(wi_id, issue_id)],
    )
    items = [{"work_item_id": str(wi_id), "id": "exec-1"}]
    await _resolve_issue_ids(items, mock_db)
    assert items[0]["issue_id"] == str(issue_id)


@pytest.mark.asyncio
async def test_sets_none_when_no_work_item_id(mock_db: AsyncMock) -> None:
    items = [{"work_item_id": None, "id": "exec-1"}]
    await _resolve_issue_ids(items, mock_db)
    assert items[0].get("issue_id") is None
    mock_db.execute.assert_not_called()


@pytest.mark.asyncio
async def test_handles_empty_list(mock_db: AsyncMock) -> None:
    items: list[dict] = []
    await _resolve_issue_ids(items, mock_db)
    mock_db.execute.assert_not_called()


@pytest.mark.asyncio
async def test_handles_work_item_not_found(mock_db: AsyncMock) -> None:
    mock_db.execute.return_value = MagicMock(all=lambda: [])
    items = [{"work_item_id": str(uuid.uuid4()), "id": "exec-1"}]
    await _resolve_issue_ids(items, mock_db)
    assert items[0]["issue_id"] is None


@pytest.mark.asyncio
async def test_resolves_multiple_executions(mock_db: AsyncMock) -> None:
    wi1, wi2 = uuid.uuid4(), uuid.uuid4()
    issue1, issue2 = uuid.uuid4(), uuid.uuid4()
    mock_db.execute.return_value = MagicMock(
        all=lambda: [(wi1, issue1), (wi2, issue2)],
    )
    items = [
        {"work_item_id": str(wi1), "id": "exec-1"},
        {"work_item_id": str(wi2), "id": "exec-2"},
        {"work_item_id": None, "id": "exec-3"},
    ]
    await _resolve_issue_ids(items, mock_db)
    assert items[0]["issue_id"] == str(issue1)
    assert items[1]["issue_id"] == str(issue2)
    assert items[2]["issue_id"] is None


@pytest.mark.asyncio
async def test_handles_work_item_with_null_issue_id(mock_db: AsyncMock) -> None:
    wi_id = uuid.uuid4()
    mock_db.execute.return_value = MagicMock(
        all=lambda: [(wi_id, None)],
    )
    items = [{"work_item_id": str(wi_id), "id": "exec-1"}]
    await _resolve_issue_ids(items, mock_db)
    assert items[0]["issue_id"] is None
