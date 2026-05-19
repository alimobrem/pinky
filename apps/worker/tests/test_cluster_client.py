"""Tests for per-cluster credential resolution in observer and activities."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest


@pytest.mark.asyncio
async def test_create_cluster_client_with_observer_binding() -> None:
    """When observer binding has credentials, create_client gets endpoint + token."""
    mock_pool = AsyncMock()
    mock_pool.fetchrow = AsyncMock(return_value={
        "api_endpoint": "https://api.cluster.example.com:6443",
        "encrypted_credential": b"encrypted-data",
    })

    with (
        patch("pinky_worker.observation.observer.get_pool", return_value=mock_pool),
        patch("pinky_worker.observation.observer.create_client", new_callable=AsyncMock) as mock_create,
        patch("pinky_worker.security.decrypt", return_value=b"decrypted-token"),
    ):
        from pinky_worker.observation.observer import _create_cluster_client
        await _create_cluster_client("cluster-uuid-1")

        mock_create.assert_called_once_with(
            api_endpoint="https://api.cluster.example.com:6443",
            token="decrypted-token",
        )


@pytest.mark.asyncio
async def test_create_cluster_client_fallback_no_credential() -> None:
    """When no observer credential exists, falls back to ambient."""
    mock_pool = AsyncMock()
    mock_pool.fetchrow = AsyncMock(return_value={
        "api_endpoint": "https://api.cluster.example.com:6443",
        "encrypted_credential": None,
    })

    with (
        patch("pinky_worker.observation.observer.get_pool", return_value=mock_pool),
        patch("pinky_worker.observation.observer.create_client", new_callable=AsyncMock) as mock_create,
    ):
        from pinky_worker.observation.observer import _create_cluster_client
        await _create_cluster_client("cluster-uuid-1")

        mock_create.assert_called_once_with()


@pytest.mark.asyncio
async def test_create_cluster_client_fallback_no_row() -> None:
    """When cluster not found in DB, falls back to ambient."""
    mock_pool = AsyncMock()
    mock_pool.fetchrow = AsyncMock(return_value=None)

    with (
        patch("pinky_worker.observation.observer.get_pool", return_value=mock_pool),
        patch("pinky_worker.observation.observer.create_client", new_callable=AsyncMock) as mock_create,
    ):
        from pinky_worker.observation.observer import _create_cluster_client
        await _create_cluster_client("cluster-uuid-1")

        mock_create.assert_called_once_with()


@pytest.mark.asyncio
async def test_create_observer_client_with_credentials() -> None:
    """Activities _create_observer_client uses binding credentials when available."""
    mock_pool = AsyncMock()
    mock_pool.fetchrow = AsyncMock(return_value={
        "api_endpoint": "https://api.prod.example.com:6443",
        "encrypted_credential": b"encrypted-data",
    })

    with (
        patch("pinky_worker.observation.k8s_client.create_client", new_callable=AsyncMock) as mock_create,
        patch("pinky_worker.security.decrypt", return_value=b"my-token"),
    ):
        from pinky_worker.execution.activities import _create_observer_client
        await _create_observer_client("00000000-0000-0000-0000-000000000001", mock_pool)

        mock_create.assert_called_once_with(
            api_endpoint="https://api.prod.example.com:6443",
            token="my-token",
        )


@pytest.mark.asyncio
async def test_create_observer_client_fallback() -> None:
    """Activities _create_observer_client falls back to ambient when no credential."""
    mock_pool = AsyncMock()
    mock_pool.fetchrow = AsyncMock(return_value=None)

    with patch("pinky_worker.observation.k8s_client.create_client", new_callable=AsyncMock) as mock_create:
        from pinky_worker.execution.activities import _create_observer_client
        await _create_observer_client("00000000-0000-0000-0000-000000000001", mock_pool)

        mock_create.assert_called_once_with()
