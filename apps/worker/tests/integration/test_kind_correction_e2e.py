"""Integration test: resource kind correction from work item labels."""

import json
from uuid import uuid4

import pytest

from pinky_worker.execution.activities import _normalize_steps, store_artifact, InvestigationArtifact


@pytest.mark.asyncio
async def test_normalize_steps_corrects_kind_from_labels(conn, fake_pool, cluster_id, execution_id):
    """When work item labels say 'rollout', normalize_steps should correct LLM's 'deployment'."""
    # Create work item with rollout labels
    wi_id = uuid4()
    issue_id = uuid4()
    await conn.execute(
        """INSERT INTO issues (id, cluster_id, correlation_key, title, severity, status, first_seen_at, last_seen_at, created_at)
           VALUES ($1, $2, $3, 'Rollout Issue', 'medium', 'open', now(), now(), now())""",
        issue_id, cluster_id, f"rollout-issue-{issue_id}",
    )
    await conn.execute(
        """INSERT INTO work_items (id, issue_id, cluster_id, title, labels, status, created_at)
           VALUES ($1, $2, $3, 'Demo Rollout Issue', $4, 'in_progress', now())""",
        wi_id, issue_id, cluster_id,
        json.dumps({"kind": "rollout", "namespace": "guestbook", "name": "demo-rollout"}),
    )

    # Update execution to link to this work item
    await conn.execute(
        "UPDATE executions SET work_item_id = $1 WHERE id = $2",
        wi_id, execution_id,
    )

    # LLM generates steps with wrong kind
    llm_steps = [
        {
            "action": "patch",
            "resource_kind": "deployment",
            "resource_name": "demo-rollout",
            "resource_namespace": "guestbook",
            "params": {"patch": {"spec": {"replicas": 3}}},
            "description": "Scale up",
            "risk": "low",
        }
    ]

    # Normalize with actual_kind from labels
    corrected = _normalize_steps(llm_steps, actual_kind="rollout")

    assert len(corrected) == 1
    assert corrected[0]["resource_kind"] == "rollout", \
        f"Expected 'rollout' but got '{corrected[0]['resource_kind']}'"
    assert corrected[0]["resource"] == "rollout/demo-rollout"


@pytest.mark.asyncio
async def test_normalize_preserves_correct_kind():
    """When LLM gets the kind right, normalization shouldn't change it."""
    steps = [
        {
            "action": "patch",
            "resource_kind": "rollout",
            "resource_name": "demo",
            "resource_namespace": "default",
            "params": {},
            "description": "Patch rollout",
            "risk": "low",
        }
    ]

    corrected = _normalize_steps(steps, actual_kind="rollout")
    assert corrected[0]["resource_kind"] == "rollout"


@pytest.mark.asyncio
async def test_api_path_for_corrected_kind():
    """Corrected kind should produce the right K8s API path."""
    from pinky_worker.execution.activities import _api_path

    # After correction to rollout, API path should use argoproj.io
    path = _api_path("rollout", "guestbook", "demo-rollout")
    assert "argoproj.io" in path
    assert "rollouts/demo-rollout" in path

    # Uncorrected deployment would use apps/v1
    path = _api_path("deployment", "guestbook", "demo-rollout")
    assert "apps/v1" in path
    assert "deployments/demo-rollout" in path
