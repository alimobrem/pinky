"""Tests for stale artifact_refs cleanup at investigation start."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest


@pytest.fixture
def mock_pool() -> AsyncMock:
    pool = AsyncMock()
    pool.fetchrow = AsyncMock(return_value=None)
    return pool


@pytest.mark.asyncio
async def test_gather_evidence_clears_stale_artifact_refs(mock_pool: AsyncMock) -> None:
    """gather_evidence should clear approval_id/changeset_digest/plan_steps from artifact_refs."""
    with (
        patch("pinky_worker.db.get_pool", AsyncMock(return_value=mock_pool)),
        patch("pinky_worker.observation.k8s_client.create_client", AsyncMock()),
        patch("pinky_worker.observation.k8s_client.list_pods", AsyncMock(return_value=[])),
        patch("pinky_worker.observation.k8s_client.list_events", AsyncMock(return_value=[])),
        patch("pinky_worker.llm.redaction.redact_evidence_sections", lambda s: s),
        patch("temporalio.activity.heartbeat"),
    ):
        from pinky_worker.execution.activities import gather_evidence
        await gather_evidence("issue-123", "cluster-1", skill_tools=None, execution_id="exec-1")

    cleanup_call = mock_pool.execute.call_args_list[0]
    sql = cleanup_call[0][0]
    assert "approval_id" in sql
    assert "changeset_digest" in sql
    assert "plan_steps" in sql
    assert "target_resources" in sql


@pytest.mark.asyncio
async def test_gather_evidence_only_clears_when_approval_exists(mock_pool: AsyncMock) -> None:
    """The cleanup query uses WHERE artifact_refs ? 'approval_id' to avoid unnecessary writes."""
    with (
        patch("pinky_worker.db.get_pool", AsyncMock(return_value=mock_pool)),
        patch("pinky_worker.observation.k8s_client.create_client", AsyncMock()),
        patch("pinky_worker.observation.k8s_client.list_pods", AsyncMock(return_value=[])),
        patch("pinky_worker.observation.k8s_client.list_events", AsyncMock(return_value=[])),
        patch("pinky_worker.llm.redaction.redact_evidence_sections", lambda s: s),
        patch("temporalio.activity.heartbeat"),
    ):
        from pinky_worker.execution.activities import gather_evidence
        await gather_evidence("issue-123", "cluster-1")

    cleanup_sql = mock_pool.execute.call_args_list[0][0][0]
    assert "artifact_refs ? 'approval_id'" in cleanup_sql
