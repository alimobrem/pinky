"""Tests that admin-only routes reject non-admin users with 403."""

from fastapi.testclient import TestClient


ADMIN_ONLY_ROUTES = [
    ("POST", "/api/v1/clusters", {"display_name": "test", "api_endpoint": "https://test"}),
    ("DELETE", "/api/v1/clusters/00000000-0000-0000-0000-000000000001", None),
    ("POST", "/api/v1/definitions", {"kind": "scanner", "name": "t", "frontmatter": {}, "body": "x"}),
    ("DELETE", "/api/v1/definitions/scanner/test", None),
    ("POST", "/api/v1/webhook-subscriptions", {"name": "t", "url": "https://t", "event_patterns": ["*"]}),
    ("DELETE", "/api/v1/webhook-subscriptions/fake-id", None),
    ("POST", "/api/v1/policy-rules", {"name": "t", "conditions": {}, "action": {"type": "observe"}}),
    ("PUT", "/api/v1/policy-rules/fake-id", {"name": "t", "conditions": {}, "action": {"type": "observe"}}),
    ("DELETE", "/api/v1/policy-rules/fake-id", None),
    ("POST", "/api/v1/policy-rules/evaluate", {"scanner": "test"}),
]


def test_admin_routes_reject_non_admin(non_admin_client: TestClient) -> None:
    for method, path, body in ADMIN_ONLY_ROUTES:
        if method == "POST":
            response = non_admin_client.post(path, json=body)
        elif method == "PUT":
            response = non_admin_client.put(path, json=body)
        elif method == "DELETE":
            response = non_admin_client.delete(path)
        else:
            raise ValueError(f"Unknown method: {method}")

        assert response.status_code == 403, f"{method} {path} should reject non-admin, got {response.status_code}"


def test_admin_routes_allow_admin(authed_client: TestClient) -> None:
    response = authed_client.post("/api/v1/definitions", json={
        "kind": "scanner",
        "name": "admin-test",
        "frontmatter": {},
        "body": "# test",
    })
    assert response.status_code == 201


def test_read_routes_allow_non_admin(non_admin_client: TestClient) -> None:
    read_routes = [
        "/api/v1/clusters",
        "/api/v1/definitions",
        "/api/v1/webhook-subscriptions",
        "/api/v1/policy-rules",
        "/api/v1/work-items",
        "/api/v1/issues",
        "/api/v1/history",
        "/api/v1/alerts",
    ]
    for path in read_routes:
        response = non_admin_client.get(path)
        assert response.status_code == 200, f"GET {path} should allow non-admin, got {response.status_code}"
