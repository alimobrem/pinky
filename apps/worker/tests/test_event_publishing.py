"""Tests for pg_notify event publishing — payload safety and dual-channel delivery."""

from __future__ import annotations

import json
import uuid
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class _FakeConn:
    def __init__(self, pool: "FakePool"):
        self._pool = pool

    async def execute(self, query: str, *args: object) -> None:
        self._pool.calls.append((query, *args))

    async def fetch(self, query: str, *args: object) -> list:
        return []

    async def fetchrow(self, query: str, *args: object):
        return await self._pool.fetchrow(query, *args)

    @asynccontextmanager
    async def transaction(self):
        yield


class FakePool:
    def __init__(self):
        self.calls: list[tuple[str, ...]] = []

    async def execute(self, query: str, *args: object) -> None:
        self.calls.append((query, *args))

    async def fetchrow(self, query: str, *args):
        if "executions" in query and "SELECT status" in query:
            return {"status": "pending", "execution_type": "investigation",
                    "work_item_id": None, "cluster_id": uuid.uuid4()}
        return None

    @asynccontextmanager
    async def acquire(self):
        yield _FakeConn(self)

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


class TestEmitCommandEvent:
    @pytest.mark.asyncio
    async def test_publishes_to_both_channels(self) -> None:
        from pinky_worker.execution.activities import _emit_command_event

        pool = FakePool()
        exec_id = str(uuid.uuid4())

        await _emit_command_event(pool, exec_id, 500, "oc scale deploy web --replicas=3", "scaled", 0, "scale", "deploy/web")

        notify_calls = pool.pg_notify_calls()
        channels = [ch for ch, _ in notify_calls]
        assert "pinky_watch" in channels
        assert f"pinky_execution_{exec_id}" in channels

    @pytest.mark.asyncio
    async def test_payload_contains_command_fields(self) -> None:
        from pinky_worker.execution.activities import _emit_command_event

        pool = FakePool()
        exec_id = str(uuid.uuid4())

        await _emit_command_event(pool, exec_id, 1, "oc delete pod web", "deleted", 0, "delete_pod", "pod/web")

        insert_calls = [(q, *a) for q, *a in pool.calls if "INSERT INTO execution_events" in q]
        assert len(insert_calls) == 1
        payload = json.loads(insert_calls[0][5])
        assert payload["command"] == "oc delete pod web"
        assert payload["output"] == "deleted"
        assert payload["exit_code"] == 0
        assert payload["action"] == "delete_pod"

    @pytest.mark.asyncio
    async def test_skips_when_no_execution_id(self) -> None:
        from pinky_worker.execution.activities import _emit_command_event

        pool = FakePool()
        await _emit_command_event(pool, "", 1, "oc test", "ok", 0, "test", "x")
        assert pool.pg_notify_calls() == []


class TestBuildOcCommand:
    def test_scale(self) -> None:
        from pinky_worker.execution.activities import _build_oc_command
        assert _build_oc_command("scale", "deployment", "web", "default", {"replicas": 3}) == "oc scale deployment web -n default --replicas=3"

    def test_patch(self) -> None:
        from pinky_worker.execution.activities import _build_oc_command
        cmd = _build_oc_command("patch", "deployment", "web", "ns", {"patch": {"spec": {"replicas": 2}}})
        assert cmd.startswith("oc patch deployment web -n ns -p '")
        assert '"replicas": 2' in cmd

    def test_delete_pod(self) -> None:
        from pinky_worker.execution.activities import _build_oc_command
        assert _build_oc_command("delete_pod", "pod", "web-abc", "default", {}) == "oc delete pod web-abc -n default"

    def test_rollback(self) -> None:
        from pinky_worker.execution.activities import _build_oc_command
        assert _build_oc_command("rollback", "deployment", "web", "default", {}) == "oc rollout undo deployment/web -n default"


class TestAutoCompleteOnRemediation:
    @pytest.mark.asyncio
    async def test_remediation_verified_completes_task(self) -> None:
        from pinky_worker.execution.activities import ExecutionEventPayload, emit_execution_event

        exec_id = str(uuid.uuid4())
        wi_id = uuid.uuid4()
        issue_id = uuid.uuid4()

        class FakePoolWithFetch(FakePool):
            async def fetchrow(self, query, *args):
                if "SELECT status" in query and "executions" in query:
                    return {
                        "status": "running",
                        "execution_type": "remediation",
                        "work_item_id": wi_id,
                        "cluster_id": uuid.uuid4(),
                    }
                if "work_items" in query and "SELECT status" in query:
                    return {"status": "in_progress", "cluster_id": uuid.uuid4()}
                if "issue_id" in query:
                    return {"issue_id": issue_id}
                return None

        pool = FakePoolWithFetch()

        with patch("pinky_worker.db.get_pool", AsyncMock(return_value=pool)):
            await emit_execution_event(ExecutionEventPayload(
                execution_id=exec_id, event_type="completed", sequence=100,
                payload={"verification_passed": True},
            ))

        all_calls_str = str(pool.calls)
        assert "work_items" in all_calls_str and "done" in all_calls_str
        assert "issues" in all_calls_str and "resolved" in all_calls_str

    @pytest.mark.asyncio
    async def test_investigation_does_not_complete_task(self) -> None:
        from pinky_worker.execution.activities import ExecutionEventPayload, emit_execution_event

        exec_id = str(uuid.uuid4())

        class FakePoolWithFetch(FakePool):
            async def fetchrow(self, query, *args):
                if "SELECT status" in query and "executions" in query:
                    return {
                        "status": "running",
                        "execution_type": "investigation",
                        "work_item_id": uuid.uuid4(),
                        "cluster_id": uuid.uuid4(),
                    }
                return None

        pool = FakePoolWithFetch()

        with patch("pinky_worker.db.get_pool", AsyncMock(return_value=pool)):
            await emit_execution_event(ExecutionEventPayload(
                execution_id=exec_id, event_type="completed", sequence=100,
                payload={"confidence": 0.8},
            ))

        queries = [q for q, *_ in pool.calls]
        assert not any("work_items SET status = 'done'" in q for q in queries)

    @pytest.mark.asyncio
    async def test_verification_failed_does_not_complete(self) -> None:
        from pinky_worker.execution.activities import ExecutionEventPayload, emit_execution_event

        exec_id = str(uuid.uuid4())

        class FakePoolWithFetch(FakePool):
            async def fetchrow(self, query, *args):
                if "SELECT status" in query and "executions" in query:
                    return {
                        "status": "running",
                        "execution_type": "remediation",
                        "work_item_id": uuid.uuid4(),
                        "cluster_id": uuid.uuid4(),
                    }
                return None

        pool = FakePoolWithFetch()

        with patch("pinky_worker.db.get_pool", AsyncMock(return_value=pool)):
            await emit_execution_event(ExecutionEventPayload(
                execution_id=exec_id, event_type="completed", sequence=100,
                payload={"verification_passed": False},
            ))

        queries = [q for q, *_ in pool.calls]
        assert not any("work_items SET status = 'done'" in q for q in queries)


class TestStateMachineGuard:
    @pytest.mark.asyncio
    async def test_completed_to_completed_blocked(self) -> None:
        from pinky_worker.execution.activities import ExecutionEventPayload, emit_execution_event

        exec_id = str(uuid.uuid4())

        class FakePoolWithFetch(FakePool):
            async def fetchrow(self, query, *args):
                if "SELECT status" in query and "executions" in query:
                    return {
                        "status": "completed",
                        "execution_type": "remediation",
                        "work_item_id": uuid.uuid4(),
                        "cluster_id": uuid.uuid4(),
                    }
                return None

        pool = FakePoolWithFetch()

        with patch("pinky_worker.db.get_pool", AsyncMock(return_value=pool)):
            await emit_execution_event(ExecutionEventPayload(
                execution_id=exec_id, event_type="completed", sequence=200,
                payload={"verification_passed": True},
            ))

        status_updates = [q for q, *_ in pool.calls if "UPDATE executions" in q and "status" in q]
        assert len(status_updates) == 0

    @pytest.mark.asyncio
    async def test_progress_event_not_blocked_by_state_machine(self) -> None:
        from pinky_worker.execution.activities import ExecutionEventPayload, emit_execution_event

        exec_id = str(uuid.uuid4())

        class FakePoolWithFetch(FakePool):
            async def fetchrow(self, query, *args):
                if "SELECT status" in query and "executions" in query:
                    return {
                        "status": "running",
                        "execution_type": "remediation",
                        "work_item_id": uuid.uuid4(),
                        "cluster_id": uuid.uuid4(),
                    }
                return None

        pool = FakePoolWithFetch()

        with patch("pinky_worker.db.get_pool", AsyncMock(return_value=pool)):
            await emit_execution_event(ExecutionEventPayload(
                execution_id=exec_id, event_type="progress", sequence=50,
                payload={"step": 1},
            ))

        insert_calls = [q for q, *_ in pool.calls if "INSERT INTO execution_events" in q]
        assert len(insert_calls) == 1


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

            async def fetch(self, query, *args):
                return []

            async def fetchrow(self, query, *args):
                return None

            @asynccontextmanager
            async def transaction(self):
                yield

        class FakePoolWithFetch:
            def __init__(self):
                self.conn = FakeConn()
                self.execute = AsyncMock()

            async def fetch(self, query, *args):
                return [stale_issue]

            async def fetchrow(self, query, *args):
                if "work_items" in query:
                    return {"status": "ready", "cluster_id": "cluster-1"}
                return None

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

        class FakeConn2:
            def __init__(self):
                self.executed: list[tuple] = []

            async def execute(self, query, *args):
                self.executed.append((query, args))

            async def fetch(self, query, *args):
                return []

            async def fetchrow(self, query, *args):
                return {"id": uuid.uuid4(), "payload": {"resolve_count": 1}}

            @asynccontextmanager
            async def transaction(self):
                yield

        class FakePoolWithFetch:
            def __init__(self):
                self.conn = FakeConn2()
                self.execute = AsyncMock()

            async def fetch(self, query, *args):
                return [stale_issue]

            async def fetchrow(self, query, *args):
                if "work_items" in query:
                    return {"status": "ready", "cluster_id": "cluster-1"}
                return None

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
