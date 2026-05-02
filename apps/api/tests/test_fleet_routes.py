from fastapi.testclient import TestClient


def test_list_clusters_requires_auth(unauthed_client: TestClient) -> None:
    response = unauthed_client.get("/api/v1/clusters")
    assert response.status_code == 401


def test_list_clusters(authed_client: TestClient) -> None:
    response = authed_client.get("/api/v1/clusters")
    assert response.status_code == 200
    assert "items" in response.json()


def test_list_bindings(authed_client: TestClient) -> None:
    response = authed_client.get("/api/v1/cluster-bindings")
    assert response.status_code == 200
    assert "items" in response.json()


def test_list_service_bindings(authed_client: TestClient) -> None:
    response = authed_client.get("/api/v1/service-bindings")
    assert response.status_code == 200
    assert "items" in response.json()
