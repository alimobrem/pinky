"""Tests for all API routes — verifies endpoints return correct shapes."""

from fastapi.testclient import TestClient

from pinky_api.app import app

client = TestClient(app)

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


def test_all_list_endpoints_return_paginated_shape() -> None:
    for endpoint in PAGINATED_ENDPOINTS:
        response = client.get(endpoint)
        assert response.status_code == 200, f"{endpoint} returned {response.status_code}"
        data = response.json()
        assert "items" in data, f"{endpoint} missing 'items'"
        assert "has_more" in data or "next_cursor" in data, f"{endpoint} missing pagination"


def test_work_item_lifecycle_endpoints_exist() -> None:
    for action in ["accept", "start", "complete"]:
        response = client.post(f"/api/v1/work-items/fake-id/{action}")
        assert response.status_code == 200


def test_work_item_reassign() -> None:
    response = client.post("/api/v1/work-items/fake-id/reassign?assignee_id=user-2")
    assert response.status_code == 200


def test_execution_approve() -> None:
    response = client.post(
        "/api/v1/executions/fake-id/approve",
        json={"changeset_digest": "sha256:abc"},
    )
    assert response.status_code == 200


def test_execution_reject() -> None:
    response = client.post(
        "/api/v1/executions/fake-id/reject",
        json={"reason": "too risky"},
    )
    assert response.status_code == 200


def test_definition_crud() -> None:
    response = client.post("/api/v1/definitions", json={
        "kind": "scanner",
        "name": "test-scanner",
        "frontmatter": {"resource_kinds": ["Pod"]},
        "body": "# Test Scanner",
    })
    assert response.status_code == 201

    response = client.delete("/api/v1/definitions/scanner/test-scanner")
    assert response.status_code == 204


def test_webhook_crud() -> None:
    response = client.post("/api/v1/webhook-subscriptions", json={
        "name": "slack-alerts",
        "url": "https://hooks.slack.com/test",
        "event_patterns": ["work_item.*"],
        "formatter": "slack",
    })
    assert response.status_code == 201

    response = client.delete("/api/v1/webhook-subscriptions/fake-id")
    assert response.status_code == 204


def test_policy_rule_crud() -> None:
    response = client.post("/api/v1/policy-rules", json={
        "name": "test-rule",
        "priority": 50,
        "conditions": {"severity_gte": "critical"},
        "action": {"type": "investigate"},
    })
    assert response.status_code == 201

    response = client.post("/api/v1/policy-rules/evaluate", json={
        "scanner": "pod-health",
        "severity": "critical",
    })
    assert response.status_code == 200


def test_analytics_endpoints() -> None:
    response = client.get("/api/v1/analytics/roi")
    assert response.status_code == 200

    response = client.get("/api/v1/analytics/scanners")
    assert response.status_code == 200

    response = client.get("/api/v1/analytics/export?format=json")
    assert response.status_code == 200


def test_sse_stream_endpoints_registered() -> None:
    routes = [r.path for r in app.routes if hasattr(r, "path")]
    assert "/api/v1/streams/work-items" in routes
    assert "/api/v1/streams/watch" in routes
    assert "/api/v1/streams/issues" in routes
    assert "/api/v1/streams/executions/{execution_id}" in routes
