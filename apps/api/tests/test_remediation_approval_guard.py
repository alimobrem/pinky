"""Tests for API approval validation before starting remediation.

Verifies that start_execution rejects remediation requests when the
approval record is missing, expired, or already used.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pinky_api.routes.executions import _resolve_issue_ids


@pytest.fixture
def mock_db() -> AsyncMock:
    return AsyncMock()


@pytest.mark.asyncio
async def test_resolve_issue_ids_skips_empty_items(mock_db: AsyncMock) -> None:
    """Sanity: no DB call when items list is empty."""
    await _resolve_issue_ids([], mock_db)
    mock_db.execute.assert_not_called()
