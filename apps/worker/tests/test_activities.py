"""Tests for execution activities — the building blocks of Brain workflows.

Covers: compute_evidence_hash, EvidenceBundle, _normalize_step, _normalize_steps,
emit_execution_event, validate_approval, gather_evidence, store_artifact,
_build_oc_command, _parse_structured_response.
"""

from __future__ import annotations

import json
import uuid
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pinky_worker.execution.activities import (
    EvidenceBundle,
    ExecutionEventPayload,
    InvestigationArtifact,
    _build_oc_command,
    _EVENT_TO_STATUS,
    _normalize_step,
    _normalize_steps,
    _parse_structured_response,
    compute_evidence_hash,
)


# ---------------------------------------------------------------------------
# Helpers / FakePool
# ---------------------------------------------------------------------------

class FakePool:
    """In-memory pool stub that tracks calls and returns configurable results."""

    def __init__(
        self,
        fetchrow_results: list[dict | None] | None = None,
        execute_side_effect: Exception | None = None,
    ) -> None:
        self.executed: list[tuple] = []
        self.fetchrow_calls: list[tuple] = []
        self._fetchrow_results = list(fetchrow_results) if fetchrow_results else []
        self._fetchrow_idx = 0
        self._execute_side_effect = execute_side_effect

    async def execute(self, query: str, *args) -> None:
        if self._execute_side_effect:
            raise self._execute_side_effect
        self.executed.append((query, args))

    async def fetchrow(self, query: str, *args) -> dict | None:
        self.fetchrow_calls.append((query, args))
        if self._fetchrow_idx < len(self._fetchrow_results):
            result = self._fetchrow_results[self._fetchrow_idx]
            self._fetchrow_idx += 1
            return result
        return None

    def acquire(self) -> _FakeAcquire:
        return _FakeAcquire(self)


class _FakeAcquire:
    def __init__(self, pool: FakePool) -> None:
        self._pool = pool

    async def __aenter__(self) -> FakeConn:
        return FakeConn(self._pool)

    async def __aexit__(self, *args: object) -> None:
        pass


class FakeConn:
    """Fake connection returned by pool.acquire() — supports transaction()."""

    def __init__(self, pool: FakePool) -> None:
        self._pool = pool

    async def execute(self, query: str, *args) -> None:
        self._pool.executed.append((query, args))

    async def fetchrow(self, query: str, *args) -> dict | None:
        return await self._pool.fetchrow(query, *args)

    @asynccontextmanager
    async def transaction(self):
        yield


# ---------------------------------------------------------------------------
# compute_evidence_hash
# ---------------------------------------------------------------------------

class TestComputeEvidenceHash:
    def test_deterministic(self) -> None:
        sections = {"status": "running", "events": "none"}
        h1 = compute_evidence_hash(sections)
        h2 = compute_evidence_hash(sections)
        assert h1 == h2

    def test_differs_on_content(self) -> None:
        h1 = compute_evidence_hash({"status": "running"})
        h2 = compute_evidence_hash({"status": "failed"})
        assert h1 != h2

    def test_order_independent(self) -> None:
        h1 = compute_evidence_hash({"a": "1", "b": "2"})
        h2 = compute_evidence_hash({"b": "2", "a": "1"})
        assert h1 == h2

    def test_length_is_16(self) -> None:
        h = compute_evidence_hash({"k": "v"})
        assert len(h) == 16

    def test_empty_sections(self) -> None:
        h = compute_evidence_hash({})
        assert isinstance(h, str)
        assert len(h) == 16


# ---------------------------------------------------------------------------
# EvidenceBundle
# ---------------------------------------------------------------------------

class TestEvidenceBundle:
    def test_construction(self) -> None:
        bundle = EvidenceBundle(
            issue_id="i1",
            cluster_id="c1",
            fingerprint="fp1",
            evidence_hash="eh1",
            sections={"status": "running"},
        )
        assert bundle.issue_id == "i1"
        assert not bundle.truncated

    def test_defaults(self) -> None:
        bundle = EvidenceBundle(
            issue_id="i1", cluster_id="c1", fingerprint="fp", evidence_hash="eh",
        )
        assert bundle.sections == {}
        assert bundle.resource_snapshots == []
        assert bundle.events == []
        assert bundle.metrics == []
        assert bundle.gathered_at == ""
        assert bundle.resource_kind == ""


# ---------------------------------------------------------------------------
# _EVENT_TO_STATUS mapping
# ---------------------------------------------------------------------------

class TestEventToStatusMapping:
    def test_started_maps_to_running(self) -> None:
        assert _EVENT_TO_STATUS["started"] == "running"

    def test_completed_maps_to_completed(self) -> None:
        assert _EVENT_TO_STATUS["completed"] == "completed"

    def test_failed_maps_to_failed(self) -> None:
        assert _EVENT_TO_STATUS["failed"] == "failed"

    def test_approval_required_maps(self) -> None:
        assert _EVENT_TO_STATUS["approval_required"] == "waiting_for_approval"

    def test_approval_granted_maps_to_running(self) -> None:
        assert _EVENT_TO_STATUS["approval_granted"] == "running"

    def test_approval_rejected_maps_to_failed(self) -> None:
        assert _EVENT_TO_STATUS["approval_rejected"] == "failed"

    def test_timed_out_maps(self) -> None:
        assert _EVENT_TO_STATUS["timed_out"] == "timed_out"

    def test_unmapped_event_returns_none(self) -> None:
        assert _EVENT_TO_STATUS.get("progress") is None
        assert _EVENT_TO_STATUS.get("tool_used") is None


# ---------------------------------------------------------------------------
# _parse_structured_response
# ---------------------------------------------------------------------------

class TestParseStructuredResponse:
    def test_extracts_json_block(self) -> None:
        content = 'Some analysis.\n```json\n{"summary": "test"}\n```\nMore text.'
        result = _parse_structured_response(content)
        assert result == {"summary": "test"}

    def test_returns_empty_dict_when_no_json(self) -> None:
        result = _parse_structured_response("No JSON here.")
        assert result == {}

    def test_returns_empty_dict_on_invalid_json(self) -> None:
        content = '```json\n{invalid json}\n```'
        result = _parse_structured_response(content)
        assert result == {}

    def test_multiline_json(self) -> None:
        content = '```json\n{\n  "summary": "test",\n  "confidence": 0.9\n}\n```'
        result = _parse_structured_response(content)
        assert result["summary"] == "test"
        assert result["confidence"] == 0.9


# ---------------------------------------------------------------------------
# _build_oc_command
# ---------------------------------------------------------------------------

class TestBuildOcCommand:
    def test_scale_command(self) -> None:
        cmd = _build_oc_command("scale", "deployment", "web", "prod", {"replicas": 3})
        assert cmd == "oc scale deployment web -n prod --replicas=3"

    def test_scale_default_replicas(self) -> None:
        cmd = _build_oc_command("scale", "deployment", "web", "prod", {})
        assert "--replicas=1" in cmd

    def test_patch_command(self) -> None:
        patch_body = {"spec": {"replicas": 2}}
        cmd = _build_oc_command("patch", "deployment", "web", "prod", {"patch": patch_body})
        assert "oc patch deployment web -n prod" in cmd
        assert json.dumps(patch_body) in cmd

    def test_delete_pod_command(self) -> None:
        cmd = _build_oc_command("delete_pod", "pod", "web-abc", "prod", {})
        assert cmd == "oc delete pod web-abc -n prod"

    def test_rollback_command(self) -> None:
        cmd = _build_oc_command("rollback", "deployment", "web", "prod", {})
        assert cmd == "oc rollout undo deployment/web -n prod"

    def test_unknown_action_fallback(self) -> None:
        cmd = _build_oc_command("restart", "deployment", "web", "prod", {})
        assert cmd == "oc restart deployment/web -n prod"


# ---------------------------------------------------------------------------
# _normalize_step / _normalize_steps
# ---------------------------------------------------------------------------

class TestNormalizeStep:
    def test_basic_step(self) -> None:
        step = {"resource_kind": "deployment", "resource_name": "web", "action": "patch",
                "resource_namespace": "prod", "params": {"patch": {}}}
        result = _normalize_step(step)
        assert result is not None
        assert result["action"] == "patch"
        assert result["resource"] == "deployment/web"
        assert result["namespace"] == "prod"
        assert result["resource_kind"] == "deployment"
        assert result["resource_name"] == "web"

    def test_rejects_step_without_name(self) -> None:
        step = {"resource_kind": "deployment", "action": "patch"}
        result = _normalize_step(step)
        assert result is None

    def test_unknown_action_defaults_to_patch(self) -> None:
        step = {"resource_name": "web", "action": "restart"}
        result = _normalize_step(step)
        assert result is not None
        assert result["action"] == "patch"

    def test_valid_actions_pass_through(self) -> None:
        for action in ("scale", "patch", "delete_pod", "rollback"):
            step = {"resource_name": "web", "action": action}
            result = _normalize_step(step)
            assert result is not None
            assert result["action"] == action

    def test_missing_action_defaults_to_patch(self) -> None:
        step = {"resource_name": "web"}
        result = _normalize_step(step)
        assert result is not None
        assert result["action"] == "patch"

    def test_kind_correction_from_work_item_labels(self) -> None:
        step = {"resource_kind": "deployment", "resource_name": "demo", "action": "patch"}
        result = _normalize_step(step, actual_kind="rollout")
        assert result is not None
        assert result["resource_kind"] == "rollout"

    def test_kind_correction_pod_to_statefulset(self) -> None:
        step = {"resource_kind": "pod", "resource_name": "db-0", "action": "delete_pod"}
        result = _normalize_step(step, actual_kind="statefulset")
        assert result is not None
        assert result["resource_kind"] == "statefulset"

    def test_no_correction_without_actual_kind(self) -> None:
        step = {"resource_kind": "deployment", "resource_name": "web", "action": "patch"}
        result = _normalize_step(step)
        assert result is not None
        assert result["resource_kind"] == "deployment"

    def test_no_correction_when_actual_kind_unknown(self) -> None:
        step = {"resource_kind": "deployment", "resource_name": "web", "action": "patch"}
        result = _normalize_step(step, actual_kind="customwidget")
        assert result is not None
        assert result["resource_kind"] == "deployment"

    def test_slash_resource_format(self) -> None:
        step = {"resource": "rollout/demo-app", "action": "patch"}
        result = _normalize_step(step)
        assert result is not None
        assert result["resource_kind"] == "rollout"
        assert result["resource_name"] == "demo-app"

    def test_resource_string_without_slash_as_name(self) -> None:
        step = {"resource": "my-pod", "action": "delete_pod"}
        result = _normalize_step(step)
        assert result is not None
        assert result["resource_name"] == "my-pod"

    def test_defaults_to_deployment_when_kind_empty(self) -> None:
        step = {"resource_name": "web", "action": "patch"}
        result = _normalize_step(step)
        assert result is not None
        assert result["resource_kind"] == "deployment"

    def test_namespace_falls_back_to_default(self) -> None:
        step = {"resource_name": "web", "action": "patch"}
        result = _normalize_step(step)
        assert result is not None
        assert result["namespace"] == "default"

    def test_namespace_from_resource_namespace(self) -> None:
        step = {"resource_name": "web", "resource_namespace": "staging"}
        result = _normalize_step(step)
        assert result is not None
        assert result["namespace"] == "staging"

    def test_namespace_from_namespace_key(self) -> None:
        step = {"resource_name": "web", "namespace": "staging"}
        result = _normalize_step(step)
        assert result is not None
        assert result["namespace"] == "staging"

    def test_risk_defaults_to_medium(self) -> None:
        step = {"resource_name": "web"}
        result = _normalize_step(step)
        assert result is not None
        assert result["risk"] == "medium"

    def test_risk_preserved(self) -> None:
        step = {"resource_name": "web", "risk": "high"}
        result = _normalize_step(step)
        assert result is not None
        assert result["risk"] == "high"

    def test_description_auto_generated(self) -> None:
        step = {"resource_name": "web", "action": "scale"}
        result = _normalize_step(step)
        assert result is not None
        assert "scale" in result["description"]
        assert "web" in result["description"]

    def test_description_preserved(self) -> None:
        step = {"resource_name": "web", "description": "Scale up the web deployment"}
        result = _normalize_step(step)
        assert result is not None
        assert result["description"] == "Scale up the web deployment"

    def test_kind_correction_unknown_kind_to_known_actual(self) -> None:
        """When step kind is NOT in _KIND_TO_API but actual_kind IS, correct it."""
        step = {"resource_kind": "foobar", "resource_name": "x", "action": "patch"}
        result = _normalize_step(step, actual_kind="daemonset")
        assert result is not None
        assert result["resource_kind"] == "daemonset"


class TestNormalizeSteps:
    def test_filters_invalid_steps(self) -> None:
        steps = [
            {"resource_name": "web", "action": "patch"},
            {"action": "scale"},  # no name — rejected
            {"resource_name": "db", "action": "rollback"},
        ]
        result = _normalize_steps(steps)
        assert len(result) == 2

    def test_empty_list(self) -> None:
        assert _normalize_steps([]) == []

    def test_passes_actual_kind_through(self) -> None:
        steps = [{"resource_kind": "deployment", "resource_name": "web", "action": "patch"}]
        result = _normalize_steps(steps, actual_kind="rollout")
        assert len(result) == 1
        assert result[0]["resource_kind"] == "rollout"

    def test_all_rejected(self) -> None:
        steps = [
            {"action": "patch"},  # no name
            {"resource_kind": "pod"},  # no name
        ]
        result = _normalize_steps(steps)
        assert result == []


# ---------------------------------------------------------------------------
# emit_execution_event
# ---------------------------------------------------------------------------

class TestEmitExecutionEvent:
    @pytest.mark.asyncio
    async def test_state_transition_started(self) -> None:
        exec_id = uuid.uuid4()
        pool = FakePool(fetchrow_results=[
            # transition_execution fetchrow
            {"status": "pending", "execution_type": "investigation",
             "work_item_id": None, "cluster_id": uuid.uuid4()},
            # exec_row fetchrow after transition
            {"status": "running", "execution_type": "investigation",
             "work_item_id": None, "cluster_id": uuid.uuid4()},
        ])

        with (
            patch("pinky_worker.db.get_pool", AsyncMock(return_value=pool)),
            patch("pinky_worker.events.emit_domain_event", AsyncMock()),
        ):
            from pinky_worker.execution.activities import emit_execution_event
            await emit_execution_event(ExecutionEventPayload(
                execution_id=str(exec_id),
                event_type="started", sequence=0, payload={},
            ))

        insert_calls = [c for c in pool.executed if "INSERT INTO execution_events" in c[0]]
        assert len(insert_calls) >= 1

    @pytest.mark.asyncio
    async def test_auto_complete_on_verified_remediation(self) -> None:
        """When event_type=completed, verification_passed=True, execution_type=remediation
        → work_item transitions to done."""
        exec_id = uuid.uuid4()
        wi_id = uuid.uuid4()
        issue_id = uuid.uuid4()
        cluster_id = uuid.uuid4()

        pool = FakePool(fetchrow_results=[
            # transition_execution fetchrow
            {"status": "running", "execution_type": "remediation",
             "work_item_id": wi_id, "cluster_id": cluster_id},
            # exec_row after transition
            {"status": "completed", "execution_type": "remediation",
             "work_item_id": wi_id, "cluster_id": cluster_id},
            # transition_work_item fetchrow (inside auto-complete)
            {"status": "in_progress", "cluster_id": cluster_id},
            # issue_row fetchrow
            {"issue_id": issue_id},
        ])

        with (
            patch("pinky_worker.db.get_pool", AsyncMock(return_value=pool)),
            patch("pinky_worker.events.emit_domain_event", AsyncMock()),
        ):
            from pinky_worker.execution.activities import emit_execution_event
            await emit_execution_event(ExecutionEventPayload(
                execution_id=str(exec_id),
                event_type="completed", sequence=1,
                payload={"verification_passed": True},
            ))

        # Should have updated the execution outcome to verified_fixed
        outcome_calls = [c for c in pool.executed if "verified_fixed" in str(c)]
        assert len(outcome_calls) >= 1

        # Should have updated the issue to resolved
        resolve_calls = [c for c in pool.executed if "resolved" in str(c)]
        assert len(resolve_calls) >= 1

    @pytest.mark.asyncio
    async def test_no_auto_complete_for_investigation(self) -> None:
        """Investigation completions should NOT trigger auto-complete to done."""
        exec_id = uuid.uuid4()
        wi_id = uuid.uuid4()
        cluster_id = uuid.uuid4()

        pool = FakePool(fetchrow_results=[
            # transition_execution fetchrow
            {"status": "running", "execution_type": "investigation",
             "work_item_id": wi_id, "cluster_id": cluster_id},
            # exec_row after transition
            {"status": "completed", "execution_type": "investigation",
             "work_item_id": wi_id, "cluster_id": cluster_id},
        ])

        with (
            patch("pinky_worker.db.get_pool", AsyncMock(return_value=pool)),
            patch("pinky_worker.events.emit_domain_event", AsyncMock()),
        ):
            from pinky_worker.execution.activities import emit_execution_event
            await emit_execution_event(ExecutionEventPayload(
                execution_id=str(exec_id),
                event_type="completed", sequence=1,
                payload={"verification_passed": True},
            ))

        # Should NOT have auto-completed work item (no verified_fixed)
        outcome_calls = [c for c in pool.executed if "verified_fixed" in str(c)]
        assert len(outcome_calls) == 0

    @pytest.mark.asyncio
    async def test_no_auto_complete_without_verification_passed(self) -> None:
        """Remediation completed but without verification_passed should not auto-complete."""
        exec_id = uuid.uuid4()
        wi_id = uuid.uuid4()
        cluster_id = uuid.uuid4()

        pool = FakePool(fetchrow_results=[
            {"status": "running", "execution_type": "remediation",
             "work_item_id": wi_id, "cluster_id": cluster_id},
            {"status": "completed", "execution_type": "remediation",
             "work_item_id": wi_id, "cluster_id": cluster_id},
        ])

        with (
            patch("pinky_worker.db.get_pool", AsyncMock(return_value=pool)),
            patch("pinky_worker.events.emit_domain_event", AsyncMock()),
        ):
            from pinky_worker.execution.activities import emit_execution_event
            await emit_execution_event(ExecutionEventPayload(
                execution_id=str(exec_id),
                event_type="completed", sequence=1,
                payload={},  # no verification_passed
            ))

        outcome_calls = [c for c in pool.executed if "verified_fixed" in str(c)]
        assert len(outcome_calls) == 0

    @pytest.mark.asyncio
    async def test_pg_notify_failure_swallowed(self) -> None:
        """pg_notify failure should be logged but not raised."""
        exec_id = uuid.uuid4()
        cluster_id = uuid.uuid4()

        call_count = 0
        original_results = [
            {"status": "pending", "execution_type": "investigation",
             "work_item_id": None, "cluster_id": cluster_id},
            {"status": "running", "execution_type": "investigation",
             "work_item_id": None, "cluster_id": cluster_id},
        ]

        class NotifyFailPool(FakePool):
            """Pool that fails on pg_notify calls."""

            async def execute(self, query: str, *args) -> None:
                if "pg_notify" in query:
                    raise RuntimeError("connection lost")
                self.executed.append((query, args))

        pool = NotifyFailPool(fetchrow_results=original_results)

        with (
            patch("pinky_worker.db.get_pool", AsyncMock(return_value=pool)),
            patch("pinky_worker.events.emit_domain_event", AsyncMock()),
        ):
            from pinky_worker.execution.activities import emit_execution_event
            # Should not raise despite pg_notify failure
            await emit_execution_event(ExecutionEventPayload(
                execution_id=str(exec_id),
                event_type="started", sequence=0, payload={},
            ))

    @pytest.mark.asyncio
    async def test_uuid_normalization_strips_investigation_prefix(self) -> None:
        exec_id = uuid.uuid4()
        pool = FakePool(fetchrow_results=[
            {"status": "pending", "execution_type": "investigation",
             "work_item_id": None, "cluster_id": uuid.uuid4()},
            {"status": "running", "execution_type": "investigation",
             "work_item_id": None, "cluster_id": uuid.uuid4()},
        ])

        with (
            patch("pinky_worker.db.get_pool", AsyncMock(return_value=pool)),
            patch("pinky_worker.events.emit_domain_event", AsyncMock()),
        ):
            from pinky_worker.execution.activities import emit_execution_event
            await emit_execution_event(ExecutionEventPayload(
                execution_id=f"investigation-{exec_id}",
                event_type="started", sequence=0, payload={},
            ))

        insert_calls = [c for c in pool.executed if "INSERT INTO execution_events" in c[0]]
        assert len(insert_calls) >= 1
        assert insert_calls[0][1][1] == exec_id

    @pytest.mark.asyncio
    async def test_uuid_normalization_strips_remediation_prefix(self) -> None:
        exec_id = uuid.uuid4()
        pool = FakePool(fetchrow_results=[
            {"status": "pending", "execution_type": "remediation",
             "work_item_id": None, "cluster_id": uuid.uuid4()},
            {"status": "running", "execution_type": "remediation",
             "work_item_id": None, "cluster_id": uuid.uuid4()},
        ])

        with (
            patch("pinky_worker.db.get_pool", AsyncMock(return_value=pool)),
            patch("pinky_worker.events.emit_domain_event", AsyncMock()),
        ):
            from pinky_worker.execution.activities import emit_execution_event
            await emit_execution_event(ExecutionEventPayload(
                execution_id=f"remediation-{exec_id}",
                event_type="started", sequence=0, payload={},
            ))

        insert_calls = [c for c in pool.executed if "INSERT INTO execution_events" in c[0]]
        assert len(insert_calls) >= 1
        assert insert_calls[0][1][1] == exec_id

    @pytest.mark.asyncio
    async def test_unmapped_event_type_no_status_change(self) -> None:
        """Event types not in _EVENT_TO_STATUS should not trigger status transitions."""
        exec_id = uuid.uuid4()
        pool = FakePool(fetchrow_results=[
            # exec_row fetchrow (no transition_execution call since no target_status)
            {"status": "running", "execution_type": "investigation",
             "work_item_id": None, "cluster_id": uuid.uuid4()},
        ])

        with (
            patch("pinky_worker.db.get_pool", AsyncMock(return_value=pool)),
            patch("pinky_worker.events.emit_domain_event", AsyncMock()),
        ):
            from pinky_worker.execution.activities import emit_execution_event
            await emit_execution_event(ExecutionEventPayload(
                execution_id=str(exec_id),
                event_type="progress", sequence=5, payload={"step": "analyzing"},
            ))

        status_calls = [c for c in pool.executed if "UPDATE executions" in c[0]]
        assert len(status_calls) == 0


# ---------------------------------------------------------------------------
# validate_approval
# ---------------------------------------------------------------------------

class TestValidateApproval:
    @pytest.mark.asyncio
    async def test_valid_approval(self) -> None:
        pool = FakePool(fetchrow_results=[{
            "status": "pending",
            "expires_at": datetime.now(UTC) + timedelta(hours=1),
            "changeset_digest": "abc123",
        }])
        with patch("pinky_worker.db.get_pool", AsyncMock(return_value=pool)):
            from pinky_worker.execution.activities import validate_approval
            result = await validate_approval(str(uuid.uuid4()), "abc123")
        assert result["valid"] is True

    @pytest.mark.asyncio
    async def test_expired_approval(self) -> None:
        pool = FakePool(fetchrow_results=[{
            "status": "pending",
            "expires_at": datetime.now(UTC) - timedelta(hours=1),
            "changeset_digest": "abc123",
        }])
        with patch("pinky_worker.db.get_pool", AsyncMock(return_value=pool)):
            from pinky_worker.execution.activities import validate_approval
            result = await validate_approval(str(uuid.uuid4()), "abc123")
        assert result["valid"] is False
        assert "expired" in result["reason"]

    @pytest.mark.asyncio
    async def test_wrong_changeset_digest(self) -> None:
        pool = FakePool(fetchrow_results=[{
            "status": "pending",
            "expires_at": datetime.now(UTC) + timedelta(hours=1),
            "changeset_digest": "abc123",
        }])
        with patch("pinky_worker.db.get_pool", AsyncMock(return_value=pool)):
            from pinky_worker.execution.activities import validate_approval
            result = await validate_approval(str(uuid.uuid4()), "wrong_digest")
        assert result["valid"] is False
        assert "changed" in result["reason"]

    @pytest.mark.asyncio
    async def test_missing_approval(self) -> None:
        pool = FakePool(fetchrow_results=[None])
        with patch("pinky_worker.db.get_pool", AsyncMock(return_value=pool)):
            from pinky_worker.execution.activities import validate_approval
            result = await validate_approval(str(uuid.uuid4()), "abc123")
        assert result["valid"] is False
        assert "not found" in result["reason"]

    @pytest.mark.asyncio
    async def test_empty_digest_rejected(self) -> None:
        pool = FakePool(fetchrow_results=[{
            "status": "pending",
            "expires_at": datetime.now(UTC) + timedelta(hours=1),
            "changeset_digest": "abc123",
        }])
        with patch("pinky_worker.db.get_pool", AsyncMock(return_value=pool)):
            from pinky_worker.execution.activities import validate_approval
            result = await validate_approval(str(uuid.uuid4()), "")
        assert result["valid"] is False
        assert "required" in result["reason"]

    @pytest.mark.asyncio
    async def test_already_approved_status(self) -> None:
        pool = FakePool(fetchrow_results=[{
            "status": "approved",
            "expires_at": datetime.now(UTC) + timedelta(hours=1),
            "changeset_digest": "abc123",
        }])
        with patch("pinky_worker.db.get_pool", AsyncMock(return_value=pool)):
            from pinky_worker.execution.activities import validate_approval
            result = await validate_approval(str(uuid.uuid4()), "abc123")
        assert result["valid"] is True

    @pytest.mark.asyncio
    async def test_rejected_status(self) -> None:
        pool = FakePool(fetchrow_results=[{
            "status": "rejected",
            "expires_at": datetime.now(UTC) + timedelta(hours=1),
            "changeset_digest": "abc123",
        }])
        with patch("pinky_worker.db.get_pool", AsyncMock(return_value=pool)):
            from pinky_worker.execution.activities import validate_approval
            result = await validate_approval(str(uuid.uuid4()), "abc123")
        assert result["valid"] is False
        assert "rejected" in result["reason"]

    @pytest.mark.asyncio
    async def test_invalidated_status(self) -> None:
        pool = FakePool(fetchrow_results=[{
            "status": "invalidated",
            "expires_at": datetime.now(UTC) + timedelta(hours=1),
            "changeset_digest": "abc123",
        }])
        with patch("pinky_worker.db.get_pool", AsyncMock(return_value=pool)):
            from pinky_worker.execution.activities import validate_approval
            result = await validate_approval(str(uuid.uuid4()), "abc123")
        assert result["valid"] is False


# ---------------------------------------------------------------------------
# gather_evidence
# ---------------------------------------------------------------------------

class TestGatherEvidence:
    @pytest.mark.asyncio
    async def test_no_skill_tools_basic_sections(self) -> None:
        """Without skill_tools, bundle should contain pods and events sections."""
        issue_id = str(uuid.uuid4())
        cluster_id = str(uuid.uuid4())

        fake_pods = [{"name": "web-abc", "status": "Running"}]
        fake_events = [{"reason": "Started", "message": "Started container"}]

        pool = FakePool(fetchrow_results=[
            None,  # wi fetchrow returns None (no work item)
            {"api_endpoint": "https://api.test:6443", "encrypted_credential": None},
        ])

        mock_k8s = AsyncMock()
        mock_k8s.close = AsyncMock()

        with (
            patch("pinky_worker.db.get_pool", AsyncMock(return_value=pool)),
            patch("pinky_worker.observation.k8s_client.create_client",
                  AsyncMock(return_value=mock_k8s)),
            patch("pinky_worker.observation.k8s_client.list_pods",
                  AsyncMock(return_value=fake_pods)),
            patch("pinky_worker.observation.k8s_client.list_events",
                  AsyncMock(return_value=fake_events)),
            patch("pinky_worker.llm.redaction.redact_evidence_sections", lambda s: s),
            patch("temporalio.activity.heartbeat"),
        ):
            from pinky_worker.execution.activities import gather_evidence
            bundle = await gather_evidence(issue_id, cluster_id)

        assert bundle.issue_id == issue_id
        assert bundle.cluster_id == cluster_id
        assert "pods" in bundle.sections or "target_resource" in bundle.sections
        assert "events" in bundle.sections

    @pytest.mark.asyncio
    async def test_k8s_client_failure_returns_error_section(self) -> None:
        """When K8s client raises, bundle should contain error fallback section."""
        issue_id = str(uuid.uuid4())
        cluster_id = str(uuid.uuid4())

        pool = FakePool(fetchrow_results=[None, None])

        with (
            patch("pinky_worker.db.get_pool", AsyncMock(return_value=pool)),
            patch(
                "pinky_worker.execution.activities._create_observer_client",
                AsyncMock(side_effect=RuntimeError("connection refused")),
            ),
            patch("pinky_worker.llm.redaction.redact_evidence_sections", lambda s: s),
            patch("temporalio.activity.heartbeat"),
        ):
            from pinky_worker.execution.activities import gather_evidence
            bundle = await gather_evidence(issue_id, cluster_id)

        assert "error" in bundle.sections
        assert "Failed to connect" in bundle.sections["error"]
        assert bundle.issue_id == issue_id

    @pytest.mark.asyncio
    async def test_with_work_item_labels_populates_resource_info(self) -> None:
        """When work item has labels, resource_namespace/name/kind should be populated."""
        issue_id = str(uuid.uuid4())
        cluster_id = str(uuid.uuid4())

        pool = FakePool(fetchrow_results=[
            # wi fetchrow
            {"title": "CrashLoopBackOff web-abc", "labels": json.dumps({
                "namespace": "prod", "name": "web-abc", "kind": "deployment",
            })},
            # _create_observer_client fetchrow
            {"api_endpoint": "https://api.test:6443", "encrypted_credential": None},
        ])

        mock_k8s = AsyncMock()
        mock_k8s.close = AsyncMock()

        with (
            patch("pinky_worker.db.get_pool", AsyncMock(return_value=pool)),
            patch("pinky_worker.observation.k8s_client.create_client",
                  AsyncMock(return_value=mock_k8s)),
            patch("pinky_worker.observation.k8s_client.list_pods",
                  AsyncMock(return_value=[{"name": "web-abc"}])),
            patch("pinky_worker.observation.k8s_client.list_events",
                  AsyncMock(return_value=[])),
            patch("pinky_worker.llm.redaction.redact_evidence_sections", lambda s: s),
            patch("temporalio.activity.heartbeat"),
        ):
            from pinky_worker.execution.activities import gather_evidence
            bundle = await gather_evidence(issue_id, cluster_id)

        assert bundle.resource_namespace == "prod"
        assert bundle.resource_name == "web-abc"
        assert bundle.resource_kind == "deployment"
        # With a resource_name, sections should have target_resource, not pods
        assert "target_resource" in bundle.sections

    @pytest.mark.asyncio
    async def test_resource_name_extracted_from_title(self) -> None:
        """When labels lack name but title matches regex, extract from title."""
        issue_id = str(uuid.uuid4())
        cluster_id = str(uuid.uuid4())

        pool = FakePool(fetchrow_results=[
            {"title": "Deployment prod/web-server is failing", "labels": None},
            {"api_endpoint": "https://api.test:6443", "encrypted_credential": None},
        ])

        mock_k8s = AsyncMock()
        mock_k8s.close = AsyncMock()

        with (
            patch("pinky_worker.db.get_pool", AsyncMock(return_value=pool)),
            patch("pinky_worker.observation.k8s_client.create_client",
                  AsyncMock(return_value=mock_k8s)),
            patch("pinky_worker.observation.k8s_client.list_pods",
                  AsyncMock(return_value=[])),
            patch("pinky_worker.observation.k8s_client.list_events",
                  AsyncMock(return_value=[])),
            patch("pinky_worker.llm.redaction.redact_evidence_sections", lambda s: s),
            patch("temporalio.activity.heartbeat"),
        ):
            from pinky_worker.execution.activities import gather_evidence
            bundle = await gather_evidence(issue_id, cluster_id)

        assert bundle.resource_kind == "deployment"
        assert bundle.resource_namespace == "prod"
        assert bundle.resource_name == "web-server"

    @pytest.mark.asyncio
    async def test_clears_stale_artifact_refs(self) -> None:
        """gather_evidence should clear stale approval refs at start."""
        pool = AsyncMock()
        pool.fetchrow = AsyncMock(return_value=None)
        pool.execute = AsyncMock()

        with (
            patch("pinky_worker.db.get_pool", AsyncMock(return_value=pool)),
            patch(
                "pinky_worker.execution.activities._create_observer_client",
                AsyncMock(side_effect=RuntimeError("fail")),
            ),
            patch("pinky_worker.llm.redaction.redact_evidence_sections", lambda s: s),
            patch("temporalio.activity.heartbeat"),
        ):
            from pinky_worker.execution.activities import gather_evidence
            await gather_evidence(str(uuid.uuid4()), str(uuid.uuid4()))

        cleanup_sql = pool.execute.call_args_list[0][0][0]
        assert "approval_id" in cleanup_sql
        assert "changeset_digest" in cleanup_sql


# ---------------------------------------------------------------------------
# store_artifact
# ---------------------------------------------------------------------------

class TestStoreArtifact:
    def _make_artifact(
        self,
        remediation_steps: list[dict] | None = None,
        execution_id: str = "",
        issue_id: str = "",
        skill_used: str = "",
    ) -> InvestigationArtifact:
        return InvestigationArtifact(
            artifact_id=str(uuid.uuid4()),
            issue_id=issue_id or str(uuid.uuid4()),
            summary="test summary",
            root_cause="test root cause",
            recommended_action="scale up",
            confidence=0.85,
            tool_calls=[],
            evidence_hash="abc123",
            created_at=datetime.now(UTC).isoformat(),
            execution_id=execution_id,
            remediation_steps=remediation_steps or [],
            skill_used=skill_used,
        )

    @pytest.mark.asyncio
    async def test_stores_as_execution_event(self) -> None:
        """Artifact should be stored as an execution_event with event_type=investigation_completed."""
        exec_id = str(uuid.uuid4())
        artifact = self._make_artifact(execution_id=exec_id)

        pool = FakePool(fetchrow_results=[
            # exec_row for analytics event
            {"work_item_id": uuid.uuid4(), "cluster_id": uuid.uuid4()},
            # wi_row for labels
            {"labels": None},
        ])

        with patch("pinky_worker.db.get_pool", AsyncMock(return_value=pool)):
            from pinky_worker.execution.activities import store_artifact
            result = await store_artifact(artifact)

        assert result == artifact.artifact_id

        insert_calls = [c for c in pool.executed if "INSERT INTO execution_events" in c[0]]
        assert len(insert_calls) >= 1
        # Verify event_type is investigation_completed
        insert_args = insert_calls[0][1]
        assert insert_args[2] == "investigation_completed"

    @pytest.mark.asyncio
    async def test_creates_approval_when_remediation_steps(self) -> None:
        """When remediation_steps are present, an approval should be created."""
        exec_id = str(uuid.uuid4())
        wi_id = uuid.uuid4()
        cluster_id = uuid.uuid4()

        artifact = self._make_artifact(
            execution_id=exec_id,
            remediation_steps=[{
                "action": "scale",
                "resource_kind": "deployment",
                "resource_name": "web",
                "resource_namespace": "prod",
                "params": {"replicas": 3},
            }],
        )

        pool = FakePool(fetchrow_results=[
            # exec_row for analytics
            {"work_item_id": wi_id, "cluster_id": cluster_id},
            # wi_row for labels
            {"labels": json.dumps({"kind": "deployment"})},
            # exec_row for approval creation
            {"work_item_id": wi_id, "cluster_id": cluster_id},
            # binding_row
            None,
        ])

        with patch("pinky_worker.db.get_pool", AsyncMock(return_value=pool)):
            from pinky_worker.execution.activities import store_artifact
            result = await store_artifact(artifact)

        assert result == artifact.artifact_id

        # Should have inserted approval
        approval_inserts = [c for c in pool.executed if "INSERT INTO approvals" in c[0]]
        assert len(approval_inserts) == 1

        # Should have updated work_items with artifact_refs
        wi_updates = [c for c in pool.executed if "UPDATE work_items" in c[0] and "artifact_refs" in c[0]]
        assert len(wi_updates) == 1

    @pytest.mark.asyncio
    async def test_no_approval_without_remediation_steps(self) -> None:
        """When remediation_steps is empty, no approval should be created."""
        exec_id = str(uuid.uuid4())
        artifact = self._make_artifact(execution_id=exec_id, remediation_steps=[])

        pool = FakePool(fetchrow_results=[
            {"work_item_id": uuid.uuid4(), "cluster_id": uuid.uuid4()},
            {"labels": None},
        ])

        with patch("pinky_worker.db.get_pool", AsyncMock(return_value=pool)):
            from pinky_worker.execution.activities import store_artifact
            await store_artifact(artifact)

        approval_inserts = [c for c in pool.executed if "INSERT INTO approvals" in c[0]]
        assert len(approval_inserts) == 0

    @pytest.mark.asyncio
    async def test_all_steps_rejected_no_approval(self) -> None:
        """If all remediation steps fail normalization, no approval should be created."""
        exec_id = str(uuid.uuid4())
        artifact = self._make_artifact(
            execution_id=exec_id,
            remediation_steps=[
                {"action": "patch"},  # no resource_name — rejected
            ],
        )

        pool = FakePool(fetchrow_results=[
            {"work_item_id": uuid.uuid4(), "cluster_id": uuid.uuid4()},
            {"labels": None},
        ])

        with patch("pinky_worker.db.get_pool", AsyncMock(return_value=pool)):
            from pinky_worker.execution.activities import store_artifact
            result = await store_artifact(artifact)

        assert result == artifact.artifact_id
        approval_inserts = [c for c in pool.executed if "INSERT INTO approvals" in c[0]]
        assert len(approval_inserts) == 0

    @pytest.mark.asyncio
    async def test_looks_up_execution_when_no_execution_id(self) -> None:
        """When artifact has no execution_id, it should look up the execution by issue_id."""
        issue_id = str(uuid.uuid4())
        exec_uuid = uuid.uuid4()
        artifact = self._make_artifact(execution_id="", issue_id=issue_id)

        pool = FakePool(fetchrow_results=[
            # exec_row lookup by issue_id
            {"id": exec_uuid},
            # exec_row for analytics
            {"work_item_id": uuid.uuid4(), "cluster_id": uuid.uuid4()},
            # wi_row for labels
            {"labels": None},
        ])

        with patch("pinky_worker.db.get_pool", AsyncMock(return_value=pool)):
            from pinky_worker.execution.activities import store_artifact
            await store_artifact(artifact)

        # Should have queried for execution by issue_id
        issue_queries = [c for c in pool.fetchrow_calls if "issue_id" in c[0]]
        assert len(issue_queries) >= 1

    @pytest.mark.asyncio
    async def test_approval_creation_failure_swallowed(self) -> None:
        """If approval creation fails, artifact should still be returned."""
        exec_id = str(uuid.uuid4())
        wi_id = uuid.uuid4()
        cluster_id = uuid.uuid4()

        artifact = self._make_artifact(
            execution_id=exec_id,
            remediation_steps=[{
                "action": "scale",
                "resource_name": "web",
                "resource_namespace": "prod",
                "params": {"replicas": 3},
            }],
        )

        class FailOnApprovalPool(FakePool):
            async def execute(self, query: str, *args) -> None:
                if "INSERT INTO approvals" in query:
                    raise RuntimeError("constraint violation")
                self.executed.append((query, args))

        pool = FailOnApprovalPool(fetchrow_results=[
            {"work_item_id": wi_id, "cluster_id": cluster_id},
            {"labels": None},
            {"work_item_id": wi_id, "cluster_id": cluster_id},
            None,  # binding_row
        ])

        with patch("pinky_worker.db.get_pool", AsyncMock(return_value=pool)):
            from pinky_worker.execution.activities import store_artifact
            # Should not raise
            result = await store_artifact(artifact)

        assert result == artifact.artifact_id

    @pytest.mark.asyncio
    async def test_kind_correction_from_work_item_labels(self) -> None:
        """Remediation steps should use kind from work item labels for correction."""
        exec_id = str(uuid.uuid4())
        wi_id = uuid.uuid4()
        cluster_id = uuid.uuid4()

        artifact = self._make_artifact(
            execution_id=exec_id,
            remediation_steps=[{
                "action": "patch",
                "resource_kind": "deployment",  # LLM says deployment
                "resource_name": "demo",
                "resource_namespace": "prod",
            }],
        )

        pool = FakePool(fetchrow_results=[
            {"work_item_id": wi_id, "cluster_id": cluster_id},
            {"labels": json.dumps({"kind": "rollout"})},  # actual kind is rollout
            {"work_item_id": wi_id, "cluster_id": cluster_id},
            None,
        ])

        with patch("pinky_worker.db.get_pool", AsyncMock(return_value=pool)):
            from pinky_worker.execution.activities import store_artifact
            await store_artifact(artifact)

        # Verify the approval was created (step was valid after correction)
        approval_inserts = [c for c in pool.executed if "INSERT INTO approvals" in c[0]]
        assert len(approval_inserts) == 1

    @pytest.mark.asyncio
    async def test_emits_analytics_event(self) -> None:
        """store_artifact should emit an investigation_completed analytics event."""
        exec_id = str(uuid.uuid4())
        cluster_id = uuid.uuid4()
        artifact = self._make_artifact(execution_id=exec_id)

        pool = FakePool(fetchrow_results=[
            {"work_item_id": uuid.uuid4(), "cluster_id": cluster_id},
            {"labels": None},
        ])

        with patch("pinky_worker.db.get_pool", AsyncMock(return_value=pool)):
            from pinky_worker.execution.activities import store_artifact
            await store_artifact(artifact)

        analytics_inserts = [c for c in pool.executed if "INSERT INTO analytics_events" in c[0]]
        assert len(analytics_inserts) >= 1


# ---------------------------------------------------------------------------
# _emit_event (internal helper)
# ---------------------------------------------------------------------------

class TestEmitEvent:
    @pytest.mark.asyncio
    async def test_skips_when_no_execution_id(self) -> None:
        from pinky_worker.execution.activities import _emit_event

        pool = FakePool()
        await _emit_event(pool, "", "started", 0, {})
        assert len(pool.executed) == 0

    @pytest.mark.asyncio
    async def test_inserts_and_notifies(self) -> None:
        from pinky_worker.execution.activities import _emit_event

        exec_id = str(uuid.uuid4())
        pool = FakePool()
        await _emit_event(pool, exec_id, "started", 1, {"key": "value"})

        assert len(pool.executed) == 3  # insert + 2 pg_notify
        assert "INSERT INTO execution_events" in pool.executed[0][0]
        assert "pg_notify" in pool.executed[1][0]
        assert "pg_notify" in pool.executed[2][0]

    @pytest.mark.asyncio
    async def test_db_error_swallowed(self) -> None:
        from pinky_worker.execution.activities import _emit_event

        pool = FakePool(execute_side_effect=RuntimeError("DB down"))
        # Should not raise
        await _emit_event(pool, str(uuid.uuid4()), "started", 0, {})


# ---------------------------------------------------------------------------
# revalidate_binding
# ---------------------------------------------------------------------------

class TestRevalidateBinding:
    @pytest.mark.asyncio
    async def test_valid_binding(self) -> None:
        pool = FakePool(fetchrow_results=[{
            "status": "valid",
            "expires_at": datetime.now(UTC) + timedelta(hours=1),
        }])
        with patch("pinky_worker.db.get_pool", AsyncMock(return_value=pool)):
            from pinky_worker.execution.activities import revalidate_binding
            result = await revalidate_binding(str(uuid.uuid4()))
        assert result["valid"] is True

    @pytest.mark.asyncio
    async def test_expiring_binding_still_valid(self) -> None:
        pool = FakePool(fetchrow_results=[{
            "status": "expiring",
            "expires_at": datetime.now(UTC) + timedelta(minutes=5),
        }])
        with patch("pinky_worker.db.get_pool", AsyncMock(return_value=pool)):
            from pinky_worker.execution.activities import revalidate_binding
            result = await revalidate_binding(str(uuid.uuid4()))
        assert result["valid"] is True

    @pytest.mark.asyncio
    async def test_expired_binding(self) -> None:
        pool = FakePool(fetchrow_results=[{
            "status": "valid",
            "expires_at": datetime.now(UTC) - timedelta(hours=1),
        }])
        with patch("pinky_worker.db.get_pool", AsyncMock(return_value=pool)):
            from pinky_worker.execution.activities import revalidate_binding
            result = await revalidate_binding(str(uuid.uuid4()))
        assert result["valid"] is False
        assert "expired" in result["reason"]

    @pytest.mark.asyncio
    async def test_revoked_binding(self) -> None:
        pool = FakePool(fetchrow_results=[{
            "status": "revoked",
            "expires_at": datetime.now(UTC) + timedelta(hours=1),
        }])
        with patch("pinky_worker.db.get_pool", AsyncMock(return_value=pool)):
            from pinky_worker.execution.activities import revalidate_binding
            result = await revalidate_binding(str(uuid.uuid4()))
        assert result["valid"] is False
        assert "revoked" in result["reason"]

    @pytest.mark.asyncio
    async def test_binding_not_found(self) -> None:
        pool = FakePool(fetchrow_results=[None])
        with patch("pinky_worker.db.get_pool", AsyncMock(return_value=pool)):
            from pinky_worker.execution.activities import revalidate_binding
            result = await revalidate_binding(str(uuid.uuid4()))
        assert result["valid"] is False
        assert "not found" in result["reason"]
