"""Logging configuration tests."""

from __future__ import annotations

import pytest

from pinky_api.logging_config import configure_logging


def test_configure_logging_dev(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PINKY_DEBUG", "true")
    configure_logging()


def test_configure_logging_prod(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PINKY_DEBUG", "false")
    configure_logging()


def test_configure_logging_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("PINKY_DEBUG", raising=False)
    configure_logging()
