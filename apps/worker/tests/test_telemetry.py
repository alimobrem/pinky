"""Tests for LLM token telemetry emission."""

from __future__ import annotations

import json
import uuid
from unittest.mock import AsyncMock, patch

import pytest


class FakePool:
    def __init__(self):
        self.calls: list[tuple[str, ...]] = []

    async def execute(self, query: str, *args: object) -> None:
        self.calls.append((query, *args))


class TestLLMTelemetryEmission:
    @pytest.mark.asyncio
    async def test_investigation_emits_llm_call_event(self) -> None:
        from pinky_worker.execution.activities import run_investigation, EvidenceBundle
        from pinky_worker.llm.provider import LLMResponse, ModelTier

        pool = FakePool()
        exec_id = str(uuid.uuid4())
        issue_id = str(uuid.uuid4())
        cluster_id = str(uuid.uuid4())

        evidence = EvidenceBundle(
            issue_id=issue_id,
            cluster_id=cluster_id,
            fingerprint="test-fp",
            resource_kind="Pod",
            resource_namespace="default",
            resource_name="web-abc",
            sections={"logs": "OOMKilled"},
            evidence_hash="abc123",
            issue_title="Pod OOMKilled",
        )

        fake_response = LLMResponse(
            content='Analysis here\n\n```json\n{"summary": "OOM", "root_cause": "Memory limit too low", "recommended_action": "Increase memory", "confidence": 0.9, "remediation_steps": [], "manual_commands": [], "verification": {"check_delay_seconds": 60, "success_criteria": "pod running"}}\n```',
            input_tokens=1500,
            output_tokens=250,
            model="gemini-2.0-flash-thinking-exp-01-21",
            provider="vertex",
            latency_ms=3200,
            cached=False,
        )

        mock_router = AsyncMock()
        mock_router.complete.return_value = fake_response
        mock_router.register = AsyncMock()

        with patch("pinky_worker.db.get_pool", AsyncMock(return_value=pool)):
            with patch("pinky_worker.llm.provider.LLMRouter", return_value=mock_router):
                with patch("pinky_worker.llm.vertex_provider.VertexProvider"):
                    with patch("temporalio.activity.heartbeat"):
                        result = await run_investigation(evidence, "test skill", exec_id)

        assert result.execution_id == exec_id

        insert_calls = [(q, *a) for q, *a in pool.calls if "INSERT INTO execution_events" in q]
        assert len(insert_calls) == 1

        query, event_id, execution_id_arg, event_type, seq, payload_json, occurred_at = insert_calls[0]
        assert event_type == "llm_call"
        assert seq == 50

        payload = json.loads(payload_json)
        assert payload["model_tier"] == ModelTier.REASONING.value
        assert payload["model"] == "gemini-2.0-flash-thinking-exp-01-21"
        assert payload["provider"] == "vertex"
        assert payload["input_tokens"] == 1500
        assert payload["output_tokens"] == 250
        assert payload["latency_ms"] == 3200
        assert payload["cache_hit"] is False
        assert payload["evidence_hash"] == "abc123"

    @pytest.mark.asyncio
    async def test_llm_call_publishes_to_pg_notify(self) -> None:
        from pinky_worker.execution.activities import run_investigation, EvidenceBundle
        from pinky_worker.llm.provider import LLMResponse

        pool = FakePool()
        exec_id = str(uuid.uuid4())

        evidence = EvidenceBundle(
            issue_id=str(uuid.uuid4()),
            cluster_id=str(uuid.uuid4()),
            fingerprint="test-fp2",
            resource_kind="Pod",
            resource_namespace="default",
            resource_name="web-abc",
            sections={"logs": "CrashLoopBackOff"},
            evidence_hash="def456",
            issue_title="Pod CrashLoop",
        )

        fake_response = LLMResponse(
            content='{"summary": "Crash", "root_cause": "Bad config", "recommended_action": "Fix", "confidence": 0.8, "remediation_steps": [], "manual_commands": [], "verification": {"check_delay_seconds": 60, "success_criteria": "running"}}',
            input_tokens=800,
            output_tokens=150,
            model="gemini-2.0-flash-thinking-exp-01-21",
            provider="vertex",
            latency_ms=2100,
            cached=True,
        )

        mock_router = AsyncMock()
        mock_router.complete.return_value = fake_response
        mock_router.register = AsyncMock()

        with patch("pinky_worker.db.get_pool", AsyncMock(return_value=pool)):
            with patch("pinky_worker.llm.provider.LLMRouter", return_value=mock_router):
                with patch("pinky_worker.llm.vertex_provider.VertexProvider"):
                    with patch("temporalio.activity.heartbeat"):
                        await run_investigation(evidence, "", exec_id)

        notify_calls = [
            (args[0], args[1])
            for query, *args in pool.calls
            if "pg_notify" in query and len(args) >= 2
        ]

        assert len(notify_calls) == 2
        channels = [ch for ch, _ in notify_calls]
        assert "pinky_watch" in channels
        assert f"pinky_execution_{exec_id}" in channels

        for ch, payload_str in notify_calls:
            payload = json.loads(payload_str)
            assert payload["event_type"] == "llm_call"
            assert payload["execution_id"] == exec_id
