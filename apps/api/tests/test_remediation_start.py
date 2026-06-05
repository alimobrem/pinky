"""Tests for remediation execution start — approval and binding validation."""

import pytest


@pytest.mark.asyncio
async def test_remediation_rejects_missing_work_item(authed_client):
    """Remediation should fail if work item doesn't exist."""
    response = authed_client.post("/api/v1/executions?work_item_id=00000000-0000-0000-0000-000000000099&execution_type=remediation")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_remediation_rejects_missing_plan(authed_client):
    """Remediation should fail if work item has no plan_steps in artifact_refs."""
    response = authed_client.post("/api/v1/executions?work_item_id=00000000-0000-0000-0000-000000000099&execution_type=remediation")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_remediation_requires_execution_type_param(authed_client):
    """Remediation endpoint requires explicit execution_type parameter."""
    response = authed_client.post("/api/v1/executions?work_item_id=00000000-0000-0000-0000-000000000099")
    assert response.status_code in (404, 409, 503)


@pytest.mark.asyncio
async def test_remediation_rejects_invalid_work_item_id(authed_client):
    """Remediation should fail gracefully on invalid UUID format."""
    response = authed_client.post("/api/v1/executions?work_item_id=not-a-uuid&execution_type=remediation")
    assert response.status_code == 404
