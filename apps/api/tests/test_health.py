from fastapi.testclient import TestClient

from pinky_api.app import app


def test_healthz() -> None:
    client = TestClient(app)
    response = client.get("/api/v1/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
