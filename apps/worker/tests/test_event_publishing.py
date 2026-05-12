"""Tests for pg_notify event publishing — payload safety and dual-channel delivery."""

from __future__ import annotations

import json
import uuid
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class FakePool:
    def __init__(self):
        self.calls: list[tuple[str, ...]] = []

    async def execute(self, query: str, *args: object) -> None:
        self.calls.append((query, *args))

    def pg_notify_calls(self) -> list[tuple[str, str]]:
        return [
            (args[0], args[1])
            for query, *args in self.calls
            if "pg_notify" in query and len(args) >= 2
        ]


class TestEmitToolEvent:
    @pytest.mark.asyncio
    async def test_publishes_to_both_channels(self) -> None:
        from pinky_worker.execution.activities import _emit_tool_event

        pool = FakePool()
        exec_id = str(uuid.uuid4())

        await _emit_tool_event(pool, exec_id, "kubectl-logs", 1)

        notify_calls = pool.pg_notify_calls()
        channels = [ch for ch, _ in notify_calls]
        assert "pinky_watch" in channels
        assert f"pinky_execution_{exec_id}" in channels

    @pytest.mark.asyncio
    async def test_payloads_are_valid_json(self) -> None:
        from pinky_worker.execution.activities import _emit_tool_event

        pool = FakePool()
        exec_id = str(uuid.uuid4())

        await _emit_tool_event(pool, exec_id, "kubectl-describe", 2)

        for _, payload in pool.pg_notify_calls():
            parsed = json.loads(payload)
            assert "event_type" in parsed
            assert "execution_id" in parsed
            assert parsed["execution_id"] == exec_id

    @pytest.mark.asyncio
    async def test_skips_when_no_execution_id(self) -> None:
        from pinky_worker.execution.activities import _emit_tool_event

        pool = FakePool()
        await _emit_tool_event(pool, "", "kubectl-logs", 1)

        assert pool.pg_notify_calls() == []


class TestCorrelatorNotifyPayloads:
    def test_work_item_payload_is_safe_json(self) -> None:
        work_item_id = uuid.uuid4()
        payload = json.dumps({"event_type": "work_item.created", "aggregate_id": str(work_item_id)})
        parsed = json.loads(payload)
        assert parsed["aggregate_id"] == str(work_item_id)

    def test_issue_payload_is_safe_json(self) -> None:
        issue_id = uuid.uuid4()
        payload = json.dumps({"event_type": "issue.created", "aggregate_id": str(issue_id)})
        parsed = json.loads(payload)
        assert parsed["aggregate_id"] == str(issue_id)

    def test_uuid_with_dashes_preserved(self) -> None:
        uid = uuid.UUID("12345678-1234-5678-1234-567812345678")
        payload = json.dumps({"event_type": "test", "aggregate_id": str(uid)})
        parsed = json.loads(payload)
        assert parsed["aggregate_id"] == "12345678-1234-5678-1234-567812345678"


class TestStalenessNotifyBehavior:
    @pytest.mark.asyncio
    async def test_fresh_resolution_emits_notify(self) -> None:
        from pinky_worker.observation.observer import _sweep_stale_issues

        stale_issue = {
            "id": uuid.uuid4(),
            "correlation_key": "test-key",
            "labels": {"scanner": "pod-health", "check_id": "test"},
            "last_seen_at": __import__("datetime").datetime.now(
                __import__("datetime").UTC
            )
            - __import__("datetime").timedelta(seconds=1200),
        }

        class FakeConn:
            def __init__(self):
                self.executed: list[tuple] = []

            async def execute(self, query, *args):
                self.executed.append((query, args))

            async def fetchrow(self, query, *args):
                return None

            @asynccontextmanager
            async def transaction(self):
                yield

        class FakePoolWithFetch:
            def __init__(self):
                self.conn = FakeConn()

            async def fetch(self, query, *args):
                return [stale_issue]

            @asynccontextmanager
            async def acquire(self):
                yield self.conn

        pool = FakePoolWithFetch()
        from pinky_worker.definitions.loader import DefinitionRegistry

        registry = DefinitionRegistry()

        with patch("pinky_worker.db.get_pool", AsyncMock(return_value=pool)):
            count = await _sweep_stale_issues("cluster-1", registry, scan_healthy=True)

        assert count == 1
        notify_calls = [
            q for q, _ in pool.conn.executed if "pg_notify" in q
        ]
        assert len(notify_calls) == 1

    @pytest.mark.asyncio
    async def test_consolidation_does_not_emit_notify(self) -> None:
        from pinky_worker.observation.observer import _sweep_stale_issues

        stale_issue = {
            "id": uuid.uuid4(),
            "correlation_key": "test-key",
            "labels": {"scanner": "pod-health", "check_id": "test"},
            "last_seen_at": __import__("datetime").datetime.now(
                __import__("datetime").UTC
            )
            - __import__("datetime").timedelta(seconds=1200),
        }

        class FakeConn:
            def __init__(self):
                self.executed: list[tuple] = []

            async def execute(self, query, *args):
                self.executed.append((query, args))

            async def fetchrow(self, query, *args):
                return {"id": uuid.uuid4(), "payload": {"resolve_count": 1}}

            @asynccontextmanager
            async def transaction(self):
                yield

        class FakePoolWithFetch:
            def __init__(self):
                self.conn = FakeConn()

            async def fetch(self, query, *args):
                return [stale_issue]

            @asynccontextmanager
            async def acquire(self):
                yield self.conn

        pool = FakePoolWithFetch()
        from pinky_worker.definitions.loader import DefinitionRegistry

        registry = DefinitionRegistry()

        with patch("pinky_worker.db.get_pool", AsyncMock(return_value=pool)):
            count = await _sweep_stale_issues("cluster-1", registry, scan_healthy=True)

        assert count == 1
        notify_calls = [
            q for q, _ in pool.conn.executed if "pg_notify" in q
        ]
        assert len(notify_calls) == 0
