"""Tests for OAuth binding auto-creation logic."""

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest

TEST_PRINCIPAL_ID = UUID("00000000-0000-0000-0000-000000000010")

_SEED_PRINCIPAL_SQL = (
    "INSERT INTO principals (id, provider, subject, display_name, email, groups) "
    "VALUES (:id, 'test', 'test-subject', 'Test User', 'test@pinky.dev', '[]') "
    "ON CONFLICT DO NOTHING"
)


@pytest.mark.asyncio
async def test_binding_repo_create(authed_client):
    """BindingRepository.create() works with required fields."""
    from pinky_api.app import app
    from pinky_api.db.deps import get_db
    from pinky_api.repositories.bindings import BindingRepository

    cluster_id = uuid4()

    async for db in app.dependency_overrides[get_db]():
        from sqlalchemy import text
        await db.execute(text(_SEED_PRINCIPAL_SQL), {"id": str(TEST_PRINCIPAL_ID)})
        await db.execute(text(
            "INSERT INTO cluster_registry (id, display_name, api_endpoint, onboarding_state) "
            "VALUES (:id, 'binding-test', 'https://api.test:6443', 'ready') ON CONFLICT DO NOTHING"
        ), {"id": str(cluster_id)})
        await db.flush()

        repo = BindingRepository(db)
        binding = await repo.create(
            principal_id=TEST_PRINCIPAL_ID,
            cluster_id=cluster_id,
            cluster_username="test-user",
            binding_method="oauth",
            status="valid",
            expires_at=datetime.now(UTC) + timedelta(hours=8),
        )
        await db.flush()

        assert binding.id is not None
        assert binding.status == "valid"
        assert binding.binding_method == "oauth"

        found = await repo.get_for_cluster(TEST_PRINCIPAL_ID, cluster_id)
        assert found is not None
        assert found.id == binding.id
        break


@pytest.mark.asyncio
async def test_cluster_repo_list_all(authed_client):
    """ClusterRepository.list_all() returns all clusters."""
    from pinky_api.app import app
    from pinky_api.db.deps import get_db
    from pinky_api.repositories.clusters import ClusterRepository

    async for db in app.dependency_overrides[get_db]():
        repo = ClusterRepository(db)
        clusters = await repo.list_all()
        assert isinstance(clusters, list)
        break


@pytest.mark.asyncio
async def test_binding_refresh_token(authed_client):
    """BindingRepository.refresh_token() updates token and sets valid status."""
    from pinky_api.app import app
    from pinky_api.db.deps import get_db
    from pinky_api.repositories.bindings import BindingRepository
    from pinky_api.security.crypto import encrypt

    cluster_id = uuid4()

    async for db in app.dependency_overrides[get_db]():
        from sqlalchemy import text
        await db.execute(text(_SEED_PRINCIPAL_SQL), {"id": str(TEST_PRINCIPAL_ID)})
        await db.execute(text(
            "INSERT INTO cluster_registry (id, display_name, api_endpoint, onboarding_state) "
            "VALUES (:id, 'refresh-test', 'https://api.test:6443', 'ready') ON CONFLICT DO NOTHING"
        ), {"id": str(cluster_id)})
        await db.flush()

        repo = BindingRepository(db)
        binding = await repo.create(
            principal_id=TEST_PRINCIPAL_ID,
            cluster_id=cluster_id,
            cluster_username="test",
            binding_method="oauth",
            status="valid",
            expires_at=datetime.now(UTC) + timedelta(hours=1),
        )
        await db.flush()

        new_token = encrypt(b"new-access-token", aad=f"cluster_identity_bindings:{binding.id}")
        refreshed = await repo.refresh_token(binding.id, new_token)
        await db.flush()

        assert refreshed is not None
        assert refreshed.status == "valid"
        assert refreshed.encrypted_token == new_token
        break


@pytest.mark.asyncio
async def test_binding_list_accessible(authed_client):
    """BindingRepository.list_accessible_cluster_ids() returns valid bindings."""
    from pinky_api.app import app
    from pinky_api.db.deps import get_db
    from pinky_api.repositories.bindings import BindingRepository

    cluster_id = uuid4()

    async for db in app.dependency_overrides[get_db]():
        from sqlalchemy import text
        await db.execute(text(_SEED_PRINCIPAL_SQL), {"id": str(TEST_PRINCIPAL_ID)})
        await db.execute(text(
            "INSERT INTO cluster_registry (id, display_name, api_endpoint, onboarding_state) "
            "VALUES (:id, 'access-test', 'https://api.test:6443', 'ready') ON CONFLICT DO NOTHING"
        ), {"id": str(cluster_id)})
        await db.flush()

        repo = BindingRepository(db)
        await repo.create(
            principal_id=TEST_PRINCIPAL_ID,
            cluster_id=cluster_id,
            cluster_username="test",
            binding_method="oauth",
            status="valid",
            expires_at=datetime.now(UTC) + timedelta(hours=1),
        )
        await db.flush()

        accessible = await repo.list_accessible_cluster_ids(TEST_PRINCIPAL_ID)
        assert cluster_id in accessible
        break
