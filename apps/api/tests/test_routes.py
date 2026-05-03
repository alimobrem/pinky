"""Tests for all API routes — verifies auth enforcement and response shapes."""

from fastapi.testclient import TestClient

from pinky_api.app import app

PAGINATED_ENDPOINTS = [
    "/api/v1/work-items",
    "/api/v1/issues",
    "/api/v1/history",
    "/api/v1/alerts",
    "/api/v1/executions",
    "/api/v1/definitions",
    "/api/v1/webhook-subscriptions",
    "/api/v1/webhook-deliveries",
    "/api/v1/policy-rules",
]


def test_unauthenticated_requests_rejected(unauthed_client: TestClient) -> None:
    for endpoint in PAGINATED_ENDPOINTS:
        response = unauthed_client.get(endpoint)
        assert response.status_code == 401, f"{endpoint} should reject unauthenticated"


def test_healthz_bypasses_auth(unauthed_client: TestClient) -> None:
    response = unauthed_client.get("/api/v1/healthz")
    assert response.status_code == 200


def test_all_list_endpoints_return_paginated_shape(authed_client: TestClient) -> None:
    for endpoint in PAGINATED_ENDPOINTS:
        response = authed_client.get(endpoint)
        assert response.status_code == 200, f"{endpoint} returned {response.status_code}"
        data = response.json()
        assert "items" in data, f"{endpoint} missing 'items'"


def test_work_item_lifecycle_returns_404_for_missing(authed_client: TestClient) -> None:
    fake_uuid = "00000000-0000-0000-0000-000000000001"
    for action in ["accept", "start", "complete"]:
        response = authed_client.post(f"/api/v1/work-items/{fake_uuid}/{action}")
        assert response.status_code == 404


def test_work_item_block_returns_404_for_missing(authed_client: TestClient) -> None:
    fake_uuid = "00000000-0000-0000-0000-000000000001"
    response = authed_client.post(
        f"/api/v1/work-items/{fake_uuid}/block",
        json={"reason": "waiting on vendor fix"},
    )
    assert response.status_code == 404


def test_work_item_reassign_returns_404_for_missing(authed_client: TestClient) -> None:
    fake_uuid = "00000000-0000-0000-0000-000000000001"
    assignee = "00000000-0000-0000-0000-000000000002"
    response = authed_client.post(f"/api/v1/work-items/{fake_uuid}/reassign?assignee_id={assignee}")
    assert response.status_code == 404


def test_execution_approve_requires_temporal(authed_client: TestClient) -> None:
    response = authed_client.post(
        "/api/v1/executions/fake-id/approve",
        json={"changeset_digest": "sha256:abc"},
    )
    assert response.status_code == 503


def test_execution_reject_requires_temporal(authed_client: TestClient) -> None:
    response = authed_client.post(
        "/api/v1/executions/fake-id/reject",
        json={"reason": "too risky"},
    )
    assert response.status_code == 503


def test_definition_crud(authed_client: TestClient) -> None:
    response = authed_client.post("/api/v1/definitions", json={
        "kind": "scanner",
        "name": "test-scanner",
        "frontmatter": {"resource_kinds": ["Pod"]},
        "body": "# Test Scanner",
    })
    assert response.status_code == 201

    response = authed_client.delete("/api/v1/definitions/scanner/test-scanner")
    assert response.status_code == 204


def test_webhook_crud(authed_client: TestClient) -> None:
    response = authed_client.post("/api/v1/webhook-subscriptions", json={
        "name": "slack-alerts",
        "url": "https://hooks.slack.com/test",
        "event_patterns": ["work_item.*"],
        "formatter": "slack",
    })
    assert response.status_code == 201

    response = authed_client.delete("/api/v1/webhook-subscriptions/00000000-0000-0000-0000-000000000001")
    assert response.status_code in (204, 404)


def test_policy_rule_crud(authed_client: TestClient) -> None:
    import secrets
    rule_name = f"test-rule-{secrets.token_hex(4)}"
    response = authed_client.post("/api/v1/policy-rules", json={
        "name": rule_name,
        "priority": 50,
        "conditions": {"severity_gte": "critical"},
        "action": {"type": "investigate"},
    })
    assert response.status_code == 201

    response = authed_client.post("/api/v1/policy-rules/evaluate", json={
        "scanner": "pod-health",
        "severity": "critical",
    })
    assert response.status_code == 200


def test_analytics_endpoints(authed_client: TestClient) -> None:
    response = authed_client.get("/api/v1/analytics/roi")
    assert response.status_code == 200

    response = authed_client.get("/api/v1/analytics/scanners")
    assert response.status_code == 200


def test_sse_stream_endpoints_registered() -> None:
    routes = [r.path for r in app.routes if hasattr(r, "path")]
    assert "/api/v1/streams/work-items" in routes
    assert "/api/v1/streams/watch" in routes
    assert "/api/v1/streams/issues" in routes
    assert "/api/v1/streams/executions/{execution_id}" in routes
