"""Webhook delivery tests — pattern matching, delivery logic."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from pinky_worker.webhooks.delivery import _deliver_one, _matches_pattern


def test_matches_wildcard() -> None:
    assert _matches_pattern("work_item.created", ["*"]) is True


def test_matches_specific() -> None:
    assert _matches_pattern("work_item.created", ["work_item.created"]) is True


def test_no_match() -> None:
    assert _matches_pattern("work_item.created", ["issue.*"]) is False


def test_matches_glob() -> None:
    assert _matches_pattern("work_item.created", ["work_item.*"]) is True


def test_matches_multiple_patterns() -> None:
    assert _matches_pattern("issue.resolved", ["work_item.*", "issue.*"]) is True


def test_no_match_empty() -> None:
    assert _matches_pattern("anything", []) is False


async def test_deliver_one_success() -> None:
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.text = "ok"

    mock_client = AsyncMock()
    mock_client.post.return_value = mock_response
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("pinky_worker.webhooks.delivery.httpx.AsyncClient", return_value=mock_client):
        code, body = await _deliver_one("https://hook.test/cb", {"event": "test"})

    assert code == 200
    assert body == "ok"


async def test_deliver_one_failure() -> None:
    mock_response = AsyncMock()
    mock_response.status_code = 500
    mock_response.text = "Internal Server Error"

    mock_client = AsyncMock()
    mock_client.post.return_value = mock_response
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("pinky_worker.webhooks.delivery.httpx.AsyncClient", return_value=mock_client):
        code, body = await _deliver_one("https://hook.test/cb", {"event": "test"})

    assert code == 500
