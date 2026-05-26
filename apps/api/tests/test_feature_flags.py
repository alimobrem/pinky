"""Test feature flag API routes and service."""
from uuid import uuid4

import pytest
from httpx import AsyncClient

from pinky_api.services import feature_flags as ff_service


@pytest.fixture(autouse=True)
def clear_cache():
    ff_service.clear_cache()
    yield
    ff_service.clear_cache()


class TestFeatureFlagCRUD:
    """Test admin-only CRUD operations for feature flags."""

    async def test_create_flag_as_admin(self, authed_client: AsyncClient):
        resp = await authed_client.post(
            "/api/v1/feature-flags",
            json={"flag_name": "new_dashboard", "enabled": True, "scope_type": "global"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["flag_name"] == "new_dashboard"
        assert data["enabled"] is True
        assert data["scope_type"] == "global"
        assert data["scope_id"] is None

    async def test_create_flag_as_non_admin(self, non_admin_client: AsyncClient):
        resp = await non_admin_client.post(
            "/api/v1/feature-flags",
            json={"flag_name": "blocked_flag", "enabled": False},
        )
        assert resp.status_code == 403

    async def test_list_flags(self, authed_client: AsyncClient):
        await authed_client.post(
            "/api/v1/feature-flags",
            json={"flag_name": "flag_a", "enabled": True},
        )
        await authed_client.post(
            "/api/v1/feature-flags",
            json={"flag_name": "flag_b", "enabled": False},
        )

        resp = await authed_client.get("/api/v1/feature-flags")
        assert resp.status_code == 200
        flags = resp.json()["flags"]
        assert len(flags) >= 2
        names = [f["flag_name"] for f in flags]
        assert "flag_a" in names
        assert "flag_b" in names

    async def test_update_flag(self, authed_client: AsyncClient):
        create_resp = await authed_client.post(
            "/api/v1/feature-flags",
            json={"flag_name": "toggle_me", "enabled": False},
        )
        flag_id = create_resp.json()["id"]

        resp = await authed_client.patch(
            f"/api/v1/feature-flags/{flag_id}",
            json={"enabled": True},
        )
        assert resp.status_code == 200
        assert resp.json()["enabled"] is True

    async def test_update_nonexistent_flag(self, authed_client: AsyncClient):
        resp = await authed_client.patch(
            f"/api/v1/feature-flags/{uuid4()}",
            json={"enabled": True},
        )
        assert resp.status_code == 404

    async def test_delete_flag(self, authed_client: AsyncClient):
        create_resp = await authed_client.post(
            "/api/v1/feature-flags",
            json={"flag_name": "delete_me", "enabled": True},
        )
        flag_id = create_resp.json()["id"]

        resp = await authed_client.delete(f"/api/v1/feature-flags/{flag_id}")
        assert resp.status_code == 204

        get_resp = await authed_client.get("/api/v1/feature-flags")
        names = [f["flag_name"] for f in get_resp.json()["flags"]]
        assert "delete_me" not in names

    async def test_delete_nonexistent_flag(self, authed_client: AsyncClient):
        resp = await authed_client.delete(f"/api/v1/feature-flags/{uuid4()}")
        assert resp.status_code == 404


class TestFeatureFlagService:
    """Test feature flag evaluation service."""

    async def test_global_flag(self, authed_client: AsyncClient, db_session):
        await authed_client.post(
            "/api/v1/feature-flags",
            json={"flag_name": "global_feature", "enabled": True, "scope_type": "global"},
        )

        enabled = await ff_service.is_enabled(db_session, "global_feature")
        assert enabled is True

    async def test_disabled_flag(self, db_session):
        enabled = await ff_service.is_enabled(db_session, "nonexistent_flag")
        assert enabled is False

    async def test_principal_scoped_flag(self, authed_client: AsyncClient, db_session):
        principal_id = uuid4()
        await authed_client.post(
            "/api/v1/feature-flags",
            json={
                "flag_name": "principal_feature",
                "enabled": True,
                "scope_type": "principal",
                "scope_id": str(principal_id),
            },
        )

        enabled = await ff_service.is_enabled(
            db_session, "principal_feature", principal_id=principal_id
        )
        assert enabled is True

        enabled = await ff_service.is_enabled(
            db_session, "principal_feature", principal_id=uuid4()
        )
        assert enabled is False

    async def test_cluster_scoped_flag(self, authed_client: AsyncClient, db_session):
        cluster_id = uuid4()
        await authed_client.post(
            "/api/v1/feature-flags",
            json={
                "flag_name": "cluster_feature",
                "enabled": True,
                "scope_type": "cluster",
                "scope_id": str(cluster_id),
            },
        )

        enabled = await ff_service.is_enabled(
            db_session, "cluster_feature", cluster_id=cluster_id
        )
        assert enabled is True

        enabled = await ff_service.is_enabled(
            db_session, "cluster_feature", cluster_id=uuid4()
        )
        assert enabled is False

    async def test_cache_hit(self, authed_client: AsyncClient, db_session):
        await authed_client.post(
            "/api/v1/feature-flags",
            json={"flag_name": "cached_flag", "enabled": True},
        )

        result1 = await ff_service.is_enabled(db_session, "cached_flag")
        result2 = await ff_service.is_enabled(db_session, "cached_flag")

        assert result1 is True
        assert result2 is True

    async def test_cache_cleared_on_update(
        self, authed_client: AsyncClient, db_session
    ):
        create_resp = await authed_client.post(
            "/api/v1/feature-flags",
            json={"flag_name": "cache_test", "enabled": False},
        )
        flag_id = create_resp.json()["id"]

        result1 = await ff_service.is_enabled(db_session, "cache_test")
        assert result1 is False

        await authed_client.patch(
            f"/api/v1/feature-flags/{flag_id}",
            json={"enabled": True},
        )

        result2 = await ff_service.is_enabled(db_session, "cache_test")
        assert result2 is True
