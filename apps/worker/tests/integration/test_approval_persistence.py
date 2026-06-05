"""Integration test: approval invalidation persists correctly in DB."""

import json
from uuid import uuid4

import pytest

from pinky_worker.transitions import transition_execution


@pytest.mark.asyncio
async def test_investigation_completion_preserves_approval(conn, fake_pool, cluster_id, execution_id):
    """When investigation completes, its pending approval should NOT be invalidated."""
    approval_id = uuid4()

    # Create work item for the execution
    wi_id = uuid4()
    issue_id = uuid4()
    await conn.execute(
        """INSERT INTO issues (id, cluster_id, correlation_key, title, severity, status, first_seen_at, last_seen_at, created_at)
           VALUES ($1, $2, $3, 'Test Issue', 'medium', 'open', now(), now(), now())""",
        issue_id, cluster_id, f"test-issue-{issue_id}",
    )
    await conn.execute(
        """INSERT INTO work_items (id, issue_id, cluster_id, title, status, created_at)
           VALUES ($1, $2, $3, 'Test Work Item', 'in_progress', now())""",
        wi_id, issue_id, cluster_id,
    )

    # Create an investigation execution linked to the work item
    inv_exec_id = uuid4()
    await conn.execute(
        """INSERT INTO executions (id, work_item_id, cluster_id, execution_type, status, created_at)
           VALUES ($1, $2, $3, 'investigation', 'running', now())""",
        inv_exec_id, wi_id, cluster_id,
    )

    # Create a pending approval linked to this execution
    await conn.execute(
        """INSERT INTO approvals (id, execution_id, changeset_digest, target_resources, status, expires_at)
           VALUES ($1, $2, 'test-digest', '[]'::jsonb, 'pending', now() + interval '24 hours')""",
        approval_id, inv_exec_id,
    )

    # Transition investigation to completed
    await transition_execution(fake_pool, inv_exec_id, "completed")

    # Verify approval is still pending
    row = await conn.fetchrow("SELECT status FROM approvals WHERE id = $1", approval_id)
    assert row["status"] == "pending", f"Expected 'pending' but got '{row['status']}'"


@pytest.mark.asyncio
async def test_remediation_completion_invalidates_approval(conn, fake_pool, cluster_id, execution_id):
    """When remediation completes, its pending approval SHOULD be invalidated."""
    approval_id = uuid4()

    # Create work item for the execution
    wi_id = uuid4()
    issue_id = uuid4()
    await conn.execute(
        """INSERT INTO issues (id, cluster_id, correlation_key, title, severity, status, first_seen_at, last_seen_at, created_at)
           VALUES ($1, $2, $3, 'Test Issue', 'medium', 'open', now(), now(), now())""",
        issue_id, cluster_id, f"test-issue-{issue_id}",
    )
    await conn.execute(
        """INSERT INTO work_items (id, issue_id, cluster_id, title, status, created_at)
           VALUES ($1, $2, $3, 'Test Work Item', 'in_progress', now())""",
        wi_id, issue_id, cluster_id,
    )

    # Create a remediation execution linked to the work item
    rem_exec_id = uuid4()
    await conn.execute(
        """INSERT INTO executions (id, work_item_id, cluster_id, execution_type, status, created_at)
           VALUES ($1, $2, $3, 'remediation', 'running', now())""",
        rem_exec_id, wi_id, cluster_id,
    )

    # Create a pending approval
    await conn.execute(
        """INSERT INTO approvals (id, execution_id, changeset_digest, target_resources, status, expires_at)
           VALUES ($1, $2, 'test-digest', '[]'::jsonb, 'pending', now() + interval '24 hours')""",
        approval_id, rem_exec_id,
    )

    # Transition remediation to completed
    await transition_execution(fake_pool, rem_exec_id, "completed")

    # Verify approval is now invalidated
    row = await conn.fetchrow("SELECT status FROM approvals WHERE id = $1", approval_id)
    assert row["status"] == "invalidated", f"Expected 'invalidated' but got '{row['status']}'"
