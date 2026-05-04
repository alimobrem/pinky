"""Service health tests — verify all routes are registered and respond correctly."""

from __future__ import annotations

from fastapi.testclient import TestClient

ALL_GET_ENDPOINTS = [
    "/api/v1/work-items",
    "/api/v1/issues",
    "/api/v1/clusters",
    "/api/v1/cluster-bindings",
    # /api/v1/cluster-bindings/status requires cluster_id param — tested separately
    "/api/v1/service-bindings",
    "/api/v1/history",
    "/api/v1/alerts",
    "/api/v1/executions",
    "/api/v1/definitions",
    "/api/v1/webhook-subscriptions",
    "/api/v1/webhook-deliveries",
    "/api/v1/policy-rules",
    "/api/v1/analytics/roi",
    "/api/v1/analytics/scanners",
]


def test_healthz_responds(authed_client: TestClient) -> None:
    r = authed_client.get("/api/v1/healthz")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_healthz_bypasses_auth(unauthed_client: TestClient) -> None:
    r = unauthed_client.get("/api/v1/healthz")
    assert r.status_code == 200


def test_login_bypasses_auth(unauthed_client: TestClient) -> None:
    r = unauthed_client.get("/api/v1/auth/login", params={"provider": "openshift"})
    assert r.status_code in (200, 503)


def test_protected_endpoints_reject_unauthed(unauthed_client: TestClient) -> None:
    for endpoint in ALL_GET_ENDPOINTS:
        r = unauthed_client.get(endpoint)
        assert r.status_code == 401, f"{endpoint} returned {r.status_code}, expected 401"


def test_all_get_endpoints_respond(authed_client: TestClient) -> None:
    for endpoint in ALL_GET_ENDPOINTS:
        r = authed_client.get(endpoint)
        assert r.status_code == 200, f"{endpoint} returned {r.status_code}, expected 200"


def test_unknown_route_returns_404(authed_client: TestClient) -> None:
    r = authed_client.get("/api/v1/nonexistent")
    assert r.status_code == 404


def test_all_get_endpoints_return_json(authed_client: TestClient) -> None:
    for endpoint in ALL_GET_ENDPOINTS:
        r = authed_client.get(endpoint)
        assert r.headers.get("content-type", "").startswith("application/json"), (
            f"{endpoint} content-type: {r.headers.get('content-type')}"
        )


def test_all_responses_include_request_id(authed_client: TestClient) -> None:
    for endpoint in ALL_GET_ENDPOINTS[:5]:
        r = authed_client.get(endpoint)
        assert "x-request-id" in r.headers, f"{endpoint} missing x-request-id header"


def test_binding_status_requires_cluster_id(authed_client: TestClient) -> None:
    r = authed_client.get("/api/v1/cluster-bindings/status")
    assert r.status_code == 422

    r = authed_client.get(
        "/api/v1/cluster-bindings/status",
        params={"cluster_id": "00000000-0000-0000-0000-000000000001"},
    )
    assert r.status_code == 200


def test_bearer_token_returns_501(unauthed_client: TestClient) -> None:
    r = unauthed_client.get(
        "/api/v1/work-items",
        headers={"Authorization": "Bearer some-api-token"},
    )
    assert r.status_code == 501
    assert "not implemented" in r.json()["error"]["message"].lower()


def test_paginated_endpoints_return_items_shape(authed_client: TestClient) -> None:
    paginated = [
        "/api/v1/work-items",
        "/api/v1/issues",
        "/api/v1/clusters",
        "/api/v1/history",
        "/api/v1/alerts",
        "/api/v1/definitions",
    ]
    for endpoint in paginated:
        r = authed_client.get(endpoint)
        data = r.json()
        assert "items" in data, f"{endpoint} missing 'items' key"
        assert isinstance(data["items"], list), f"{endpoint} 'items' is not a list"
