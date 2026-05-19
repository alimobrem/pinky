"""Tests for domain event emission in observer suppress and create_task paths."""

from __future__ import annotations

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _make_decision(suppress_minutes: int = 60, action_type: str = "suppress"):
    decision = MagicMock()
    decision.action.action_type = action_type
    decision.action.suppress_duration_minutes = suppress_minutes
    decision.action.risk_class = None
    decision.action.runbook_url = None
    decision.action.skill = None
    return decision


def _make_result(issue_id: str = "issue-123"):
    result = MagicMock()
    result.issue_id = issue_id
    return result


def _make_obs():
    obs = MagicMock()
    obs.cluster_id = "cluster-1"
    obs.title = "Pod crash loop"
    obs.check_id = "crash-loop"
    obs.resource_kind = "Pod"
    obs.resource_namespace = "default"
    obs.resource_name = "app-1"
    obs.scanner = "pod-health"
    return obs


def _make_pool(conn):
    pool = AsyncMock()

    @asynccontextmanager
    async def acquire():
        yield conn

    pool.acquire = acquire
    return pool


@pytest.mark.asyncio
async def test_handle_suppress_emits_domain_event() -> None:
    mock_conn = AsyncMock()
    pool = _make_pool(mock_conn)

    with (
        patch("pinky_worker.db.get_pool", AsyncMock(return_value=pool)),
        patch("pinky_worker.observation.observer.emit_domain_event", new_callable=AsyncMock) as mock_emit,
    ):
        from pinky_worker.observation.observer import _handle_suppress
        await _handle_suppress(_make_result(), _make_decision(suppress_minutes=120))

    mock_emit.assert_called_once()
    args = mock_emit.call_args[0]
    assert args[1] == "issue.suppressed"
    assert args[2] == "issue"
    assert args[3] == "issue-123"


@pytest.mark.asyncio
async def test_handle_suppress_skips_when_no_issue_id() -> None:
    result = _make_result()
    result.issue_id = None

    with patch("pinky_worker.observation.observer.emit_domain_event", new_callable=AsyncMock) as mock_emit:
        from pinky_worker.observation.observer import _handle_suppress
        await _handle_suppress(result, _make_decision())

    mock_emit.assert_not_called()


@pytest.mark.asyncio
async def test_handle_create_task_emits_domain_event() -> None:
    mock_conn = AsyncMock()
    pool = _make_pool(mock_conn)

    with (
        patch("pinky_worker.db.get_pool", AsyncMock(return_value=pool)),
        patch("pinky_worker.observation.observer.emit_domain_event", new_callable=AsyncMock) as mock_emit,
    ):
        from pinky_worker.observation.observer import _handle_create_task
        decision = _make_decision(action_type="create_task")
        decision.action.risk_class = "high"
        await _handle_create_task(_make_result(), decision, _make_obs())

    mock_emit.assert_called_once()
    args = mock_emit.call_args[0]
    assert args[1] == "work_item.created"
    assert args[2] == "work_item"


@pytest.mark.asyncio
async def test_handle_create_task_skips_when_no_issue_id() -> None:
    result = _make_result()
    result.issue_id = None

    with patch("pinky_worker.observation.observer.emit_domain_event", new_callable=AsyncMock) as mock_emit:
        from pinky_worker.observation.observer import _handle_create_task
        await _handle_create_task(result, _make_decision(), _make_obs())

    mock_emit.assert_not_called()
