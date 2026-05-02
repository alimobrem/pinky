from fastapi.testclient import TestClient


def test_login_returns_state(unauthed_client: TestClient) -> None:
    response = unauthed_client.get("/api/v1/auth/login?provider=openshift")
    # 200 with state (provider may or may not be configured — both OK)
    assert response.status_code in (200, 503)
    if response.status_code == 200:
        assert "state" in response.json()


def test_login_rejects_unknown_provider(unauthed_client: TestClient) -> None:
    response = unauthed_client.get("/api/v1/auth/login?provider=saml")
    assert response.status_code == 400


def test_logout(authed_client: TestClient) -> None:
    response = authed_client.post("/api/v1/auth/logout")
    assert response.status_code == 200
