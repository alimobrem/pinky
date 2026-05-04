"""Contract tests — verify API response shapes match @pinky/contracts types.

These tests ensure the Python response schemas stay aligned with
the TypeScript types in packages/contracts/src/.
"""

from pinky_api.schemas.cluster import ClusterListResponse, ClusterResponse
from pinky_api.schemas.issue import IssueListResponse, IssueResponse
from pinky_api.schemas.work_item import WorkItemListResponse, WorkItemResponse


def test_work_item_response_has_all_contract_fields() -> None:
    required_fields = {
        "id", "issue_id", "cluster_id", "title", "why_now",
        "recommended_next_step", "status", "owner_id", "confidence",
        "priority", "labels", "annotations", "runbook_url",
        "created_at", "updated_at",
    }
    schema_fields = set(WorkItemResponse.model_fields.keys())
    missing = required_fields - schema_fields
    assert not missing, f"WorkItemResponse missing fields: {missing}"


def test_work_item_response_serializes() -> None:
    item = WorkItemResponse(
        id="abc",
        cluster_id="c1",
        title="Test task",
        status="ready",
    )
    data = item.model_dump()
    assert data["id"] == "abc"
    assert data["labels"] == {}
    assert data["annotations"] == {}
    assert data["confidence"] is None


def test_issue_response_has_all_contract_fields() -> None:
    required_fields = {
        "id", "cluster_id", "correlation_key", "title", "severity",
        "status", "labels", "annotations", "runbook_url",
        "first_seen_at", "last_seen_at", "resolved_at", "created_at",
    }
    schema_fields = set(IssueResponse.model_fields.keys())
    missing = required_fields - schema_fields
    assert not missing, f"IssueResponse missing fields: {missing}"


def test_cluster_response_has_all_contract_fields() -> None:
    required_fields = {
        "id", "display_name", "api_endpoint", "fleet_identifier",
        "onboarding_state", "offboarding_state", "created_at",
    }
    schema_fields = set(ClusterResponse.model_fields.keys())
    missing = required_fields - schema_fields
    assert not missing, f"ClusterResponse missing fields: {missing}"


def test_paginated_responses_have_cursor_fields() -> None:
    for cls in [WorkItemListResponse, IssueListResponse, ClusterListResponse]:
        fields = set(cls.model_fields.keys())
        assert "items" in fields, f"{cls.__name__} missing 'items'"
        assert "next_cursor" in fields, f"{cls.__name__} missing 'next_cursor'"
        assert "has_more" in fields, f"{cls.__name__} missing 'has_more'"
