"""Tests for observer investigation dispatch and error handling."""

from __future__ import annotations

import asyncio
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pinky_worker.issues.correlator import CorrelationResult


def _make_obs():
    obs = MagicMock()
    obs.fingerprint = "abc123"
    obs.correlation_key = "test-key"
    obs.check_id = "crash-loop"
    obs.resource_kind = "Pod"
    obs.resource_namespace = "default"
    obs.resource_name = "test-pod"
    return obs


def _make_decision():
    decision = MagicMock()
    decision.action.skill = None
    return decision


def _make_pool(cooldown_result=None, wi_result=None):
    """Create a fake pool with sequential fetchrow results.
    First call = cooldown check, second call = work_item lookup."""
    fake_pool = AsyncMock()
    fake_pool.fetchrow = AsyncMock(side_effect=[cooldown_result, wi_result])
    fake_pool.execute = AsyncMock()
    return fake_pool


@pytest.mark.asyncio
async def test_dispatch_handles_workflow_already_started():
    from pinky_worker.observation.observer import _dispatch_investigation

    mock_client = AsyncMock()
    mock_client.start_workflow = AsyncMock(
        side_effect=Exception("Workflow execution already started")
    )

    fake_pool = _make_pool(
        cooldown_result=None,
        wi_result={"id": uuid.uuid4()},
    )

    result = CorrelationResult(action="created", issue_id=str(uuid.uuid4()), observation_count=1)

    with patch("pinky_worker.db.get_pool", AsyncMock(return_value=fake_pool)):
        await _dispatch_investigation(
            mock_client, str(uuid.uuid4()), _make_obs(), result, _make_decision(), MagicMock(),
        )


@pytest.mark.asyncio
async def test_dispatch_creates_execution_record():
    from pinky_worker.observation.observer import _dispatch_investigation

    mock_client = AsyncMock()
    mock_client.start_workflow = AsyncMock()

    work_item_id = uuid.uuid4()
    fake_pool = _make_pool(
        cooldown_result=None,
        wi_result={"id": work_item_id},
    )

    result = CorrelationResult(action="created", issue_id=str(uuid.uuid4()), observation_count=1)

    with patch("pinky_worker.db.get_pool", AsyncMock(return_value=fake_pool)):
        await _dispatch_investigation(
            mock_client, str(uuid.uuid4()), _make_obs(), result, _make_decision(), MagicMock(),
        )

    insert_calls = [
        call for call in fake_pool.execute.call_args_list
        if "INSERT INTO executions" in str(call)
    ]
    assert len(insert_calls) == 1

    mock_client.start_workflow.assert_called_once()
    wf_id = mock_client.start_workflow.call_args.kwargs["id"]
    assert wf_id.startswith("investigation-")


@pytest.mark.asyncio
async def test_dispatch_marks_failed_on_unexpected_error():
    from pinky_worker.observation.observer import _dispatch_investigation

    mock_client = AsyncMock()
    mock_client.start_workflow = AsyncMock(
        side_effect=Exception("Temporal unavailable")
    )

    fake_pool = _make_pool(
        cooldown_result=None,
        wi_result={"id": uuid.uuid4()},
    )

    result = CorrelationResult(action="created", issue_id=str(uuid.uuid4()), observation_count=1)

    with patch("pinky_worker.db.get_pool", AsyncMock(return_value=fake_pool)):
        await _dispatch_investigation(
            mock_client, str(uuid.uuid4()), _make_obs(), result, _make_decision(), MagicMock(),
        )

    failed_calls = [
        call for call in fake_pool.execute.call_args_list
        if "UPDATE executions SET status = 'failed'" in str(call)
    ]
    assert len(failed_calls) == 1


@pytest.mark.asyncio
async def test_dispatch_skips_on_cooldown():
    from pinky_worker.observation.observer import _dispatch_investigation

    mock_client = AsyncMock()

    fake_pool = AsyncMock()
    fake_pool.fetchrow = AsyncMock(return_value={"id": uuid.uuid4(), "status": "completed"})
    fake_pool.execute = AsyncMock()

    result = CorrelationResult(action="created", issue_id=str(uuid.uuid4()), observation_count=1)

    with patch("pinky_worker.db.get_pool", AsyncMock(return_value=fake_pool)):
        await _dispatch_investigation(
            mock_client, str(uuid.uuid4()), _make_obs(), result, _make_decision(), MagicMock(),
        )

    mock_client.start_workflow.assert_not_called()


@pytest.mark.asyncio
async def test_dispatch_skips_on_recent_failure():
    from pinky_worker.observation.observer import _dispatch_investigation

    mock_client = AsyncMock()

    fake_pool = AsyncMock()
    fake_pool.fetchrow = AsyncMock(return_value={"id": uuid.uuid4(), "status": "failed"})
    fake_pool.execute = AsyncMock()

    result = CorrelationResult(action="created", issue_id=str(uuid.uuid4()), observation_count=1)

    with patch("pinky_worker.db.get_pool", AsyncMock(return_value=fake_pool)):
        await _dispatch_investigation(
            mock_client, str(uuid.uuid4()), _make_obs(), result, _make_decision(), MagicMock(),
        )

    mock_client.start_workflow.assert_not_called()


@pytest.mark.asyncio
async def test_observer_retries_temporal_connection():
    """run_observer retries Temporal connection on subsequent cycles after initial failure."""
    from pinky_worker.main import run_observer

    registry = MagicMock()
    registry.list_by_kind.return_value = []
    correlator = MagicMock()

    shutdown = asyncio.Event()
    call_count = 0

    async def mock_connect(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise ConnectionRefusedError("Temporal not ready")
        mock_client = AsyncMock()
        return mock_client

    fake_pool = AsyncMock()
    fake_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=AsyncMock())
    fake_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=False)
    conn_mock = AsyncMock()
    conn_mock.fetch = AsyncMock(return_value=[])
    fake_pool.acquire.return_value.__aenter__.return_value = conn_mock

    async def stop_after_two_cycles(*args, **kwargs):
        if call_count >= 2:
            shutdown.set()
        return fake_pool

    with (
        patch("pinky_worker.main.get_pool", side_effect=stop_after_two_cycles),
        patch("pinky_worker.main.get_settings", return_value=MagicMock(
            temporal=MagicMock(address="localhost:7233", namespace="default"),
        )),
        patch("temporalio.client.Client.connect", side_effect=mock_connect),
        patch("pinky_worker.main.os.environ.get", side_effect=lambda k, d="": {
            "PINKY_SCAN_INTERVAL": "0",
            "PINKY_TEMPORAL_ENABLED": "true",
        }.get(k, d)),
    ):
        await run_observer(registry, correlator, shutdown_event=shutdown)

    assert call_count == 2
