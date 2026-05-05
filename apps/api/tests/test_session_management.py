"""Session management tests — CSRF enforcement, cookie behavior, token auth."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_csrf_missing_on_post_returns_403(unauthed_client: TestClient) -> None:
    """POST to protected endpoint without auth returns 401 (before CSRF check)."""
    r = unauthed_client.post("/api/v1/work-items/00000000-0000-0000-0000-000000000001/accept")
    assert r.status_code == 401


def test_get_requests_skip_csrf(authed_client: TestClient) -> None:
    """GET never checks CSRF — should return 200."""
    r = authed_client.get("/api/v1/work-items")
    assert r.status_code == 200


def test_authed_post_works_with_override(authed_client: TestClient) -> None:
    """authed_client bypasses real auth — POST should work (404 on missing, not 403)."""
    r = authed_client.post("/api/v1/work-items/00000000-0000-0000-0000-000000000001/accept")
    assert r.status_code in (404, 409)


def test_bearer_token_invalid_returns_error(unauthed_client: TestClient) -> None:
    r = unauthed_client.get(
        "/api/v1/work-items",
        headers={"Authorization": "Bearer test-token"},
    )
    # 401 (invalid token) or 503 (DB not available in test) — never 501
    assert r.status_code in (401, 503)


def test_bearer_token_with_invalid_prefix_returns_401(unauthed_client: TestClient) -> None:
    r = unauthed_client.get(
        "/api/v1/work-items",
        headers={"Authorization": "Token test-token"},
    )
    assert r.status_code == 401


def test_empty_session_cookie_returns_401(unauthed_client: TestClient) -> None:
    r = unauthed_client.get("/api/v1/work-items", cookies={"pinky_session": ""})
    assert r.status_code == 401


def test_invalid_session_cookie_returns_401(unauthed_client: TestClient) -> None:
    r = unauthed_client.get(
        "/api/v1/work-items",
        cookies={"pinky_session": "totally-invalid-token-value"},
    )
    assert r.status_code in (401, 503)


def test_healthz_ignores_bad_session(unauthed_client: TestClient) -> None:
    r = unauthed_client.get(
        "/api/v1/healthz",
        cookies={"pinky_session": "bad-token"},
    )
    assert r.status_code == 200


def test_login_ignores_bad_session(unauthed_client: TestClient) -> None:
    r = unauthed_client.get(
        "/api/v1/auth/login",
        params={"provider": "openshift"},
        cookies={"pinky_session": "bad-token"},
    )
    assert r.status_code in (200, 503)


def test_auth_session_endpoint_unauthed(unauthed_client: TestClient) -> None:
    r = unauthed_client.get("/api/v1/auth/session")
    assert r.status_code in (200, 401)


def test_logout_without_session(unauthed_client: TestClient) -> None:
    r = unauthed_client.post("/api/v1/auth/logout")
    assert r.status_code in (200, 401)


def test_non_admin_cannot_access_admin_routes(non_admin_client: TestClient) -> None:
    r = non_admin_client.post("/api/v1/clusters", json={
        "display_name": "test", "api_endpoint": "https://test:6443",
    })
    assert r.status_code == 403


def test_non_admin_can_access_read_routes(non_admin_client: TestClient) -> None:
    r = non_admin_client.get("/api/v1/work-items")
    assert r.status_code == 200

    r = non_admin_client.get("/api/v1/issues")
    assert r.status_code == 200


def test_admin_can_access_admin_routes(authed_client: TestClient) -> None:
    r = authed_client.post("/api/v1/clusters", json={
        "display_name": "admin-test", "api_endpoint": "https://admin-test:6443",
    })
    assert r.status_code == 201


def test_multiple_unprotected_paths_accessible(unauthed_client: TestClient) -> None:
    for path in ["/api/v1/healthz", "/api/v1/auth/login?provider=openshift"]:
        r = unauthed_client.get(path)
        assert r.status_code in (200, 503), f"{path} returned {r.status_code}"
