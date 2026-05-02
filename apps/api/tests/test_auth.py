from fastapi.testclient import TestClient

from pinky_api.app import app

client = TestClient(app)


def test_login_returns_state() -> None:
    response = client.get("/api/v1/auth/login?provider=openshift")
    assert response.status_code == 200
    data = response.json()
    assert "state" in data
    assert data["provider"] == "openshift"


def test_login_rejects_unknown_provider() -> None:
    response = client.get("/api/v1/auth/login?provider=saml")
    assert response.status_code == 400


def test_logout_clears_cookie() -> None:
    response = client.post("/api/v1/auth/logout")
    assert response.status_code == 200
    assert "pinky_session" in response.headers.get("set-cookie", "")
