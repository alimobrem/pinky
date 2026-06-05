"""Tests for OAuth binding auto-creation logic."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest


@pytest.mark.asyncio
async def test_binding_repo_create(authed_client):
    """BindingRepository.create() works with required fields."""
    from pinky_api.app import app
    from pinky_api.db.deps import get_db
    from pinky_api.models.fleet import ClusterIdentityBinding
    from pinky_api.repositories.bindings import BindingRepository
    from sqlalchemy import select

    cluster_id = uuid4()
    principal_id = uuid4()
    subject = f"binding-test-{principal_id}"

    async for db in app.dependency_overrides[get_db]():
        from sqlalchemy import text
        await db.execute(text(
            "INSERT INTO cluster_registry (id, display_name, api_endpoint, onboarding_state) "
            "VALUES (:id, 'binding-test', 'https://api.test:6443', 'ready') "
            "ON CONFLICT (id) DO NOTHING"
        ), {"id": str(cluster_id)})
        await db.execute(text(
            "INSERT INTO principals (id, provider, subject, display_name) "
            "VALUES (:id, 'test', :subject, 'Test User') "
            "ON CONFLICT (provider, subject) DO NOTHING"
        ), {"id": str(principal_id), "subject": subject})
        await db.commit()

        repo = BindingRepository(db)
        binding = await repo.create(
            principal_id=principal_id,
            cluster_id=cluster_id,
            cluster_username="test-user",
            binding_method="oauth",
            status="valid",
            expires_at=datetime.now(UTC) + timedelta(hours=8),
        )
        await db.commit()

        assert binding.id is not None
        assert binding.status == "valid"
        assert binding.binding_method == "oauth"

        result = await db.execute(
            select(ClusterIdentityBinding).where(
                ClusterIdentityBinding.principal_id == principal_id,
                ClusterIdentityBinding.cluster_id == cluster_id
            )
        )
        found = result.scalar_one_or_none()
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
    from pinky_api.models.fleet import ClusterIdentityBinding
    from pinky_api.repositories.bindings import BindingRepository
    from pinky_api.security.crypto import encrypt
    from sqlalchemy import select

    cluster_id = uuid4()
    principal_id = uuid4()
    subject = f"refresh-test-{principal_id}"

    async for db in app.dependency_overrides[get_db]():
        from sqlalchemy import text
        await db.execute(text(
            "INSERT INTO cluster_registry (id, display_name, api_endpoint, onboarding_state) "
            "VALUES (:id, 'refresh-test', 'https://api.test:6443', 'ready') "
            "ON CONFLICT (id) DO NOTHING"
        ), {"id": str(cluster_id)})
        await db.execute(text(
            "INSERT INTO principals (id, provider, subject, display_name) "
            "VALUES (:id, 'test', :subject, 'Test') "
            "ON CONFLICT (provider, subject) DO NOTHING"
        ), {"id": str(principal_id), "subject": subject})
        await db.commit()

        repo = BindingRepository(db)
        binding = await repo.create(
            principal_id=principal_id,
            cluster_id=cluster_id,
            cluster_username="test",
            binding_method="oauth",
            status="valid",
            expires_at=datetime.now(UTC) + timedelta(hours=1),
        )
        await db.commit()

        new_token = encrypt(b"new-access-token", aad=f"cluster_identity_bindings:{binding.id}")
        refreshed = await repo.refresh_token(binding.id, new_token)
        await db.commit()

        assert refreshed is not None
        assert refreshed.status == "valid"
        assert refreshed.encrypted_token == new_token

        result = await db.execute(
            select(ClusterIdentityBinding).where(ClusterIdentityBinding.id == binding.id)
        )
        persisted = result.scalar_one_or_none()
        assert persisted is not None
        assert persisted.encrypted_token == new_token
        break


@pytest.mark.asyncio
async def test_binding_list_accessible_cluster_ids(authed_client):
    """BindingRepository.list_accessible_cluster_ids() returns only valid/expiring bindings."""
    from pinky_api.app import app
    from pinky_api.db.deps import get_db
    from pinky_api.repositories.bindings import BindingRepository

    cluster_id = uuid4()
    principal_id = uuid4()
    subject = f"access-test-{principal_id}"

    async for db in app.dependency_overrides[get_db]():
        from sqlalchemy import text
        await db.execute(text(
            "INSERT INTO cluster_registry (id, display_name, api_endpoint, onboarding_state) "
            "VALUES (:id, 'access-test', 'https://api.test:6443', 'ready') "
            "ON CONFLICT (id) DO NOTHING"
        ), {"id": str(cluster_id)})
        await db.execute(text(
            "INSERT INTO principals (id, provider, subject, display_name) "
            "VALUES (:id, 'test', :subject, 'Test') "
            "ON CONFLICT (provider, subject) DO NOTHING"
        ), {"id": str(principal_id), "subject": subject})
        await db.commit()

        repo = BindingRepository(db)
        await repo.create(
            principal_id=principal_id,
            cluster_id=cluster_id,
            cluster_username="test",
            binding_method="oauth",
            status="valid",
            expires_at=datetime.now(UTC) + timedelta(hours=1),
        )
        await db.commit()

        accessible = await repo.list_accessible_cluster_ids(principal_id)
        assert cluster_id in accessible
        break
