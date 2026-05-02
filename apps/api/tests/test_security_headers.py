from fastapi.testclient import TestClient

from pinky_api.app import app

client = TestClient(app)


def test_csp_header_present() -> None:
    response = client.get("/api/v1/healthz")
    assert "Content-Security-Policy" in response.headers
    csp = response.headers["Content-Security-Policy"]
    assert "'self'" in csp
    assert "unsafe-inline" not in csp
    assert "unsafe-eval" not in csp


def test_hsts_header_present() -> None:
    response = client.get("/api/v1/healthz")
    assert "Strict-Transport-Security" in response.headers
    assert "max-age=" in response.headers["Strict-Transport-Security"]


def test_x_content_type_options() -> None:
    response = client.get("/api/v1/healthz")
    assert response.headers.get("X-Content-Type-Options") == "nosniff"


def test_referrer_policy() -> None:
    response = client.get("/api/v1/healthz")
    assert "Referrer-Policy" in response.headers


def test_permissions_policy() -> None:
    response = client.get("/api/v1/healthz")
    assert "Permissions-Policy" in response.headers


def test_x_frame_options() -> None:
    response = client.get("/api/v1/healthz")
    assert response.headers.get("X-Frame-Options") == "DENY"
