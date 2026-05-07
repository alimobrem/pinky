"""Tests for token management security fixes."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pinky_api.routes.resources import _resolve_token


@pytest.mark.asyncio
async def test_resolve_token_rejects_expired_binding():
    expired_binding = MagicMock()
    expired_binding.encrypted_token = b"encrypted"
    expired_binding.expires_at = datetime.now(UTC) - timedelta(hours=1)
    expired_binding.id = uuid.uuid4()

    mock_db = AsyncMock()
    cluster = MagicMock(api_endpoint="https://api.test:6443")

    with (
        patch("pinky_api.routes.resources.ClusterRepository") as repo_cls,
        patch("pinky_api.routes.resources.get_cluster_binding_for_principal",
              new_callable=AsyncMock, return_value=expired_binding),
    ):
        repo_cls.return_value.get = AsyncMock(return_value=cluster)

        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await _resolve_token(uuid.uuid4(), {}, mock_db)
        assert exc_info.value.status_code == 401
        assert "expired" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_resolve_token_rejects_missing_binding():
    mock_db = AsyncMock()
    cluster = MagicMock(api_endpoint="https://api.test:6443")

    with (
        patch("pinky_api.routes.resources.ClusterRepository") as repo_cls,
        patch("pinky_api.routes.resources.get_cluster_binding_for_principal",
              new_callable=AsyncMock, return_value=None),
    ):
        repo_cls.return_value.get = AsyncMock(return_value=cluster)

        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await _resolve_token(uuid.uuid4(), {}, mock_db)
        assert exc_info.value.status_code == 401
        assert "binding required" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_resolve_token_catches_decrypt_failure():
    valid_binding = MagicMock()
    valid_binding.encrypted_token = b"corrupted"
    valid_binding.expires_at = datetime.now(UTC) + timedelta(hours=1)
    valid_binding.id = uuid.uuid4()

    mock_db = AsyncMock()
    cluster = MagicMock(api_endpoint="https://api.test:6443")

    with (
        patch("pinky_api.routes.resources.ClusterRepository") as repo_cls,
        patch("pinky_api.routes.resources.get_cluster_binding_for_principal",
              new_callable=AsyncMock, return_value=valid_binding),
        patch("pinky_api.routes.resources.decrypt", side_effect=ValueError("bad AAD")),
    ):
        repo_cls.return_value.get = AsyncMock(return_value=cluster)

        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await _resolve_token(uuid.uuid4(), {}, mock_db)
        assert exc_info.value.status_code == 401
        assert "invalid" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_resolve_token_succeeds_with_valid_binding():
    valid_binding = MagicMock()
    valid_binding.encrypted_token = b"encrypted"
    valid_binding.expires_at = datetime.now(UTC) + timedelta(hours=1)
    valid_binding.id = uuid.uuid4()

    mock_db = AsyncMock()
    cluster = MagicMock(api_endpoint="https://api.test:6443")

    with (
        patch("pinky_api.routes.resources.ClusterRepository") as repo_cls,
        patch("pinky_api.routes.resources.get_cluster_binding_for_principal",
              new_callable=AsyncMock, return_value=valid_binding),
        patch("pinky_api.routes.resources.decrypt", return_value=b"my-token"),
    ):
        repo_cls.return_value.get = AsyncMock(return_value=cluster)

        endpoint, token = await _resolve_token(uuid.uuid4(), {}, mock_db)
        assert endpoint == "https://api.test:6443"
        assert token == "my-token"
