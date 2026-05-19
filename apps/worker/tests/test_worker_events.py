"""Tests for worker-side domain event emitter."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, call

import pytest

from pinky_worker.events import CHANNEL_MAP, emit_domain_event


@pytest.fixture
def mock_conn() -> AsyncMock:
    return AsyncMock()


@pytest.mark.asyncio
async def test_emit_inserts_domain_event(mock_conn: AsyncMock) -> None:
    event_id = await emit_domain_event(
        mock_conn, "issue.created", "issue", "issue-123",
        payload={"title": "OOM"},
    )
    assert event_id
    insert_call = mock_conn.execute.call_args_list[0]
    sql = insert_call[0][0]
    assert "INSERT INTO domain_events" in sql


@pytest.mark.asyncio
async def test_emit_fires_pg_notify(mock_conn: AsyncMock) -> None:
    await emit_domain_event(
        mock_conn, "issue.created", "issue", "issue-123",
    )
    notify_call = mock_conn.execute.call_args_list[1]
    sql = notify_call[0][0]
    assert "pg_notify" in sql
    assert "pinky_issues" in sql


@pytest.mark.asyncio
async def test_emit_uses_correct_channel_for_work_item(mock_conn: AsyncMock) -> None:
    await emit_domain_event(
        mock_conn, "work_item.created", "work_item", "wi-1",
    )
    notify_call = mock_conn.execute.call_args_list[1]
    sql = notify_call[0][0]
    assert "pinky_work_items" in sql


@pytest.mark.asyncio
async def test_emit_uses_watch_channel_for_execution(mock_conn: AsyncMock) -> None:
    await emit_domain_event(
        mock_conn, "execution.started", "execution", "exec-1",
    )
    notify_call = mock_conn.execute.call_args_list[1]
    sql = notify_call[0][0]
    assert "pinky_watch" in sql


@pytest.mark.asyncio
async def test_emit_defaults_to_pinky_watch(mock_conn: AsyncMock) -> None:
    await emit_domain_event(
        mock_conn, "something.happened", "unknown_type", "id-1",
    )
    notify_call = mock_conn.execute.call_args_list[1]
    sql = notify_call[0][0]
    assert "pinky_watch" in sql


@pytest.mark.asyncio
async def test_emit_with_cluster_and_principal(mock_conn: AsyncMock) -> None:
    await emit_domain_event(
        mock_conn, "issue.created", "issue", "issue-1",
        payload={"severity": "critical"},
        cluster_id="cluster-1",
        principal_id="principal-1",
    )
    insert_call = mock_conn.execute.call_args_list[0]
    args = insert_call[0]
    # args: sql, event_id, event_type, aggregate_type, aggregate_id, payload, cluster_id, principal_id, now
    assert args[2] == "issue.created"
    assert args[6] == "cluster-1"
    assert args[7] == "principal-1"
    assert json.loads(args[5])["severity"] == "critical"


@pytest.mark.asyncio
async def test_emit_empty_payload_defaults_to_empty_dict(mock_conn: AsyncMock) -> None:
    await emit_domain_event(
        mock_conn, "issue.created", "issue", "issue-1",
    )
    insert_call = mock_conn.execute.call_args_list[0]
    args = insert_call[0]
    assert json.loads(args[5]) == {}


@pytest.mark.asyncio
async def test_emit_pg_notify_failure_does_not_raise(mock_conn: AsyncMock) -> None:
    mock_conn.execute = AsyncMock(side_effect=[None, Exception("connection lost")])
    event_id = await emit_domain_event(
        mock_conn, "issue.created", "issue", "issue-1",
    )
    assert event_id


@pytest.mark.asyncio
async def test_emit_notify_payload_contains_event_metadata(mock_conn: AsyncMock) -> None:
    await emit_domain_event(
        mock_conn, "work_item.completed", "work_item", "wi-42",
    )
    notify_call = mock_conn.execute.call_args_list[1]
    notify_payload = json.loads(notify_call[0][1])
    assert notify_payload["event_type"] == "work_item.completed"
    assert notify_payload["aggregate_type"] == "work_item"
    assert notify_payload["aggregate_id"] == "wi-42"
    assert "event_id" in notify_payload


def test_channel_map_covers_expected_types() -> None:
    assert CHANNEL_MAP["work_item"] == "pinky_work_items"
    assert CHANNEL_MAP["issue"] == "pinky_issues"
    assert CHANNEL_MAP["execution"] == "pinky_watch"
    assert CHANNEL_MAP["approval"] == "pinky_watch"
    assert CHANNEL_MAP["cluster"] == "pinky_watch"
