"""Tests for domain event emitter — channel mapping and payload construction."""

from __future__ import annotations

import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pinky_api.events import CHANNEL_MAP, emit


class TestChannelMap:
    def test_work_item_channel(self) -> None:
        assert CHANNEL_MAP["work_item"] == "pinky_work_items"

    def test_issue_channel(self) -> None:
        assert CHANNEL_MAP["issue"] == "pinky_issues"

    def test_execution_channel(self) -> None:
        assert CHANNEL_MAP["execution"] == "pinky_watch"

    def test_approval_channel(self) -> None:
        assert CHANNEL_MAP["approval"] == "pinky_watch"

    def test_cluster_channel(self) -> None:
        assert CHANNEL_MAP["cluster"] == "pinky_watch"


class TestEmit:
    @pytest.mark.asyncio
    async def test_creates_domain_event_with_fields(self) -> None:
        db = AsyncMock()
        db.flush = AsyncMock()
        raw_conn = AsyncMock()
        db.connection = AsyncMock(return_value=raw_conn)

        agg_id = uuid.uuid4()
        event = await emit(
            db, "task.created", "work_item", agg_id,
            {"title": "Pod crash"},
        )

        assert event.event_type == "task.created"
        assert event.aggregate_type == "work_item"
        assert event.aggregate_id == agg_id
        assert event.payload == {"title": "Pod crash"}
        db.add.assert_called_once_with(event)
        db.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_sets_cluster_and_principal(self) -> None:
        db = AsyncMock()
        db.flush = AsyncMock()
        raw_conn = AsyncMock()
        db.connection = AsyncMock(return_value=raw_conn)

        cluster_id = uuid.uuid4()
        principal_id = uuid.uuid4()
        event = await emit(
            db, "approval.granted", "execution", uuid.uuid4(),
            {"digest": "abc"},
            cluster_id=cluster_id,
            principal_id=principal_id,
        )

        assert event.cluster_id == cluster_id
        assert event.principal_id == principal_id

    @pytest.mark.asyncio
    async def test_sends_pg_notify_on_correct_channel(self) -> None:
        db = AsyncMock()
        db.flush = AsyncMock()
        raw_conn = AsyncMock()
        db.connection = AsyncMock(return_value=raw_conn)

        agg_id = uuid.uuid4()
        await emit(db, "task.created", "work_item", agg_id, {})

        raw_conn.execute.assert_called_once()
        call_args = raw_conn.execute.call_args
        params = call_args[0][1]
        assert params["channel"] == "pinky_work_items"
        payload = json.loads(params["payload"])
        assert payload["event_type"] == "task.created"
        assert payload["aggregate_type"] == "work_item"
        assert payload["aggregate_id"] == str(agg_id)

    @pytest.mark.asyncio
    async def test_unknown_aggregate_uses_pinky_watch(self) -> None:
        db = AsyncMock()
        db.flush = AsyncMock()
        raw_conn = AsyncMock()
        db.connection = AsyncMock(return_value=raw_conn)

        await emit(db, "custom.event", "unknown_type", uuid.uuid4(), {})

        params = raw_conn.execute.call_args[0][1]
        assert params["channel"] == "pinky_watch"

    @pytest.mark.asyncio
    async def test_pg_notify_failure_does_not_raise(self) -> None:
        db = AsyncMock()
        db.flush = AsyncMock()
        raw_conn = AsyncMock()
        raw_conn.execute.side_effect = Exception("connection lost")
        db.connection = AsyncMock(return_value=raw_conn)

        event = await emit(db, "task.created", "work_item", uuid.uuid4(), {})
        assert event.event_type == "task.created"
