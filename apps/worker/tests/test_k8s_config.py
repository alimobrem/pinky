"""Tests for K8s client auto-detection of in-cluster config."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock

import pytest


@pytest.mark.asyncio
async def test_create_client_detects_incluster_when_sa_token_exists():
    with (
        patch("pinky_worker.observation.k8s_client._SA_TOKEN", Path("/fake/token")),
        patch.object(Path, "exists", return_value=True),
        patch("pinky_worker.observation.k8s_client.config") as mock_config,
        patch("pinky_worker.observation.k8s_client.ApiClient") as mock_client,
    ):
        from pinky_worker.observation.k8s_client import create_client

        await create_client()
        mock_config.load_incluster_config.assert_called_once()


@pytest.mark.asyncio
async def test_create_client_falls_back_to_kubeconfig_when_no_sa_token():
    with (
        patch("pinky_worker.observation.k8s_client._SA_TOKEN", Path("/nonexistent")),
        patch("pinky_worker.observation.k8s_client.config") as mock_config,
        patch("pinky_worker.observation.k8s_client.ApiClient") as mock_client,
    ):
        mock_config.load_kube_config = AsyncMock()

        from pinky_worker.observation.k8s_client import create_client

        await create_client()
        mock_config.load_kube_config.assert_called_once()


@pytest.mark.asyncio
async def test_create_client_uses_explicit_kubeconfig():
    with (
        patch("pinky_worker.observation.k8s_client.config") as mock_config,
        patch("pinky_worker.observation.k8s_client.ApiClient") as mock_client,
    ):
        mock_config.load_kube_config = AsyncMock()

        from pinky_worker.observation.k8s_client import create_client

        await create_client(kubeconfig="/my/kubeconfig")
        mock_config.load_kube_config.assert_called_once_with(config_file="/my/kubeconfig")
