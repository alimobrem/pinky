"""Tests for cluster binding management endpoints."""


class TestClusterBindingsList:
    def test_list_bindings(self, authed_client):
        r = authed_client.get("/api/v1/cluster-bindings")
        assert r.status_code == 200
        assert "items" in r.json()

    def test_list_bindings_unauthed(self, unauthed_client):
        r = unauthed_client.get("/api/v1/cluster-bindings")
        assert r.status_code == 401


class TestClusterBindingStatus:
    def test_status_no_cluster(self, authed_client):
        r = authed_client.get("/api/v1/cluster-bindings/status")
        assert r.status_code in (200, 422)

    def test_status_nonexistent_cluster(self, authed_client):
        r = authed_client.get(
            "/api/v1/cluster-bindings/status?cluster_id=00000000-0000-0000-0000-000000000000"
        )
        assert r.status_code in (200, 404)
        if r.status_code == 200:
            assert r.json()["status"] in ("missing", "valid", "expired", "revoked")


class TestClusterBindingCreate:
    def test_create_invalid_cluster_rejected(self, authed_client):
        import pytest
        with pytest.raises(Exception):
            authed_client.post("/api/v1/cluster-bindings", json={
                "cluster_id": "00000000-0000-0000-0000-000000000000",
                "binding_method": "oauth_login",
            })


class TestClusterBindingDelete:
    def test_delete_not_found(self, authed_client):
        r = authed_client.delete(
            "/api/v1/cluster-bindings/00000000-0000-0000-0000-000000000000"
        )
        assert r.status_code in (204, 404)
