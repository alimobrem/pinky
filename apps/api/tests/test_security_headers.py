from fastapi.testclient import TestClient


def test_csp_header_present(unauthed_client: TestClient) -> None:
    response = unauthed_client.get("/api/v1/healthz")
    assert "Content-Security-Policy" in response.headers
    csp = response.headers["Content-Security-Policy"]
    assert "'self'" in csp
    assert "unsafe-inline" not in csp
    assert "unsafe-eval" not in csp


def test_hsts_header_present(unauthed_client: TestClient) -> None:
    response = unauthed_client.get("/api/v1/healthz")
    assert "Strict-Transport-Security" in response.headers


def test_x_content_type_options(unauthed_client: TestClient) -> None:
    response = unauthed_client.get("/api/v1/healthz")
    assert response.headers.get("X-Content-Type-Options") == "nosniff"


def test_referrer_policy(unauthed_client: TestClient) -> None:
    response = unauthed_client.get("/api/v1/healthz")
    assert "Referrer-Policy" in response.headers


def test_permissions_policy(unauthed_client: TestClient) -> None:
    response = unauthed_client.get("/api/v1/healthz")
    assert "Permissions-Policy" in response.headers


def test_x_frame_options(unauthed_client: TestClient) -> None:
    response = unauthed_client.get("/api/v1/healthz")
    assert response.headers.get("X-Frame-Options") == "DENY"


def test_error_401_has_error_schema(unauthed_client: TestClient) -> None:
    r = unauthed_client.get("/api/v1/work-items")
    assert r.status_code == 401
    data = r.json()
    assert "error" in data
    assert "code" in data["error"]
    assert "message" in data["error"]
    assert "request_id" in data["error"]


def test_error_404_has_error_schema(authed_client: TestClient) -> None:
    r = authed_client.get("/api/v1/nonexistent-route")
    assert r.status_code == 404
    data = r.json()
    assert "error" in data
    assert data["error"]["code"] == "http_404"


def test_error_422_has_error_schema(authed_client: TestClient) -> None:
    r = authed_client.get("/api/v1/cluster-bindings/status")
    assert r.status_code == 422


def test_error_responses_do_not_leak_stack_traces(unauthed_client: TestClient) -> None:
    r = unauthed_client.get("/api/v1/work-items")
    body = r.text
    assert "Traceback" not in body
    assert "File " not in body


def test_no_cors_headers_on_non_preflight(authed_client: TestClient) -> None:
    r = authed_client.get("/api/v1/healthz")
    assert "Access-Control-Allow-Origin" not in r.headers
