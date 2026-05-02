from fastapi.testclient import TestClient


def test_login_bypasses_auth(unauthed_client: TestClient) -> None:
    response = unauthed_client.get("/api/v1/auth/login?provider=openshift")
    assert response.status_code == 200
    data = response.json()
    assert "state" in data


def test_login_rejects_unknown_provider(unauthed_client: TestClient) -> None:
    response = unauthed_client.get("/api/v1/auth/login?provider=saml")
    assert response.status_code == 400


def test_logout(authed_client: TestClient) -> None:
    response = authed_client.post("/api/v1/auth/logout")
    assert response.status_code == 200
