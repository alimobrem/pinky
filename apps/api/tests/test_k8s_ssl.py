"""Tests for K8s client TLS verification behavior."""

from __future__ import annotations

import ssl
from pathlib import Path
from unittest.mock import patch

from pinky_api.k8s import _get_ssl_context


class TestGetSslContext:
    def test_debug_mode_disables_verification(self) -> None:
        with patch.dict("os.environ", {"PINKY_DEBUG": "true"}):
            assert _get_ssl_context() is False

    def test_debug_mode_case_insensitive(self) -> None:
        with patch.dict("os.environ", {"PINKY_DEBUG": "True"}):
            assert _get_ssl_context() is False

    def test_no_debug_no_ca_files_returns_true(self) -> None:
        with (
            patch.dict("os.environ", {}, clear=True),
            patch.object(Path, "exists", return_value=False),
        ):
            result = _get_ssl_context()
            assert result is True

    def test_loads_ca_when_files_exist(self) -> None:
        def fake_exists(self: Path) -> bool:
            return str(self) == "/var/run/secrets/kubernetes.io/serviceaccount/ca.crt"

        with (
            patch.dict("os.environ", {}, clear=True),
            patch.object(Path, "exists", fake_exists),
            patch("ssl.create_default_context") as mock_ctx,
        ):
            result = _get_ssl_context()
            mock_ctx.assert_called_once()
            mock_ctx.return_value.load_verify_locations.assert_called_once_with(
                "/var/run/secrets/kubernetes.io/serviceaccount/ca.crt"
            )
            assert result is mock_ctx.return_value

    def test_loads_multiple_ca_files(self) -> None:
        with (
            patch.dict("os.environ", {}, clear=True),
            patch.object(Path, "exists", return_value=True),
            patch("ssl.create_default_context") as mock_ctx,
        ):
            result = _get_ssl_context()
            assert mock_ctx.return_value.load_verify_locations.call_count == 2
            assert result is mock_ctx.return_value
