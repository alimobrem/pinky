from fastapi.testclient import TestClient

from pinky_api.app import app

client = TestClient(app)


def test_list_clusters() -> None:
    response = client.get("/api/v1/clusters")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert data["has_more"] is False


def test_list_bindings() -> None:
    response = client.get("/api/v1/cluster-bindings")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data


def test_list_service_bindings() -> None:
    response = client.get("/api/v1/service-bindings")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
