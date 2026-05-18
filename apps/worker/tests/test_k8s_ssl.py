"""Tests for TLS verification in worker K8s clients."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestActivitiesSslContext:
    def test_debug_mode_disables_verification(self) -> None:
        from pinky_worker.execution.activities import _get_ssl_context

        with patch.dict("os.environ", {"PINKY_DEBUG": "true"}):
            assert _get_ssl_context() is False

    def test_no_debug_no_ca_returns_true(self) -> None:
        from pinky_worker.execution.activities import _get_ssl_context

        with (
            patch.dict("os.environ", {}, clear=True),
            patch.object(Path, "exists", return_value=False),
        ):
            assert _get_ssl_context() is True

    def test_loads_ca_when_present(self) -> None:
        from pinky_worker.execution.activities import _get_ssl_context

        def fake_exists(self: Path) -> bool:
            return str(self) == "/var/run/secrets/kubernetes.io/serviceaccount/ca.crt"

        with (
            patch.dict("os.environ", {}, clear=True),
            patch.object(Path, "exists", fake_exists),
            patch("ssl.create_default_context") as mock_ctx,
        ):
            result = _get_ssl_context()
            mock_ctx.return_value.load_verify_locations.assert_called_once_with(
                "/var/run/secrets/kubernetes.io/serviceaccount/ca.crt"
            )
            assert result is mock_ctx.return_value


class TestObserverClientSsl:
    @pytest.mark.asyncio
    async def test_debug_mode_disables_verify_ssl(self) -> None:
        with (
            patch.dict("os.environ", {"PINKY_DEBUG": "true"}),
            patch("pinky_worker.observation.k8s_client.client") as mock_k8s,
            patch("pinky_worker.observation.k8s_client.ApiClient") as mock_api,
        ):
            mock_cfg = MagicMock()
            mock_k8s.Configuration.return_value = mock_cfg

            from pinky_worker.observation.k8s_client import create_client

            await create_client(api_endpoint="https://api:6443", token="tok")
            assert mock_cfg.verify_ssl is False

    @pytest.mark.asyncio
    async def test_production_enables_verify_ssl(self) -> None:
        with (
            patch.dict("os.environ", {}, clear=True),
            patch("pinky_worker.observation.k8s_client.client") as mock_k8s,
            patch("pinky_worker.observation.k8s_client.ApiClient") as mock_api,
            patch.object(Path, "exists", return_value=False),
        ):
            mock_cfg = MagicMock()
            mock_k8s.Configuration.return_value = mock_cfg

            from pinky_worker.observation.k8s_client import create_client

            await create_client(api_endpoint="https://api:6443", token="tok")
            assert mock_cfg.verify_ssl is True

    @pytest.mark.asyncio
    async def test_production_loads_ca_cert(self) -> None:
        def fake_exists(self: Path) -> bool:
            return str(self) == "/var/run/secrets/kubernetes.io/serviceaccount/ca.crt"

        with (
            patch.dict("os.environ", {}, clear=True),
            patch("pinky_worker.observation.k8s_client.client") as mock_k8s,
            patch("pinky_worker.observation.k8s_client.ApiClient") as mock_api,
            patch.object(Path, "exists", fake_exists),
        ):
            mock_cfg = MagicMock()
            mock_k8s.Configuration.return_value = mock_cfg

            from pinky_worker.observation.k8s_client import create_client

            await create_client(api_endpoint="https://api:6443", token="tok")
            assert mock_cfg.verify_ssl is True
            assert mock_cfg.ssl_ca_cert == "/var/run/secrets/kubernetes.io/serviceaccount/ca.crt"
