"""Tests for worker configuration."""

from __future__ import annotations

from unittest.mock import patch

from pinky_worker.config import WorkerConfig, get_settings


class TestWorkerConfig:
    def test_defaults(self) -> None:
        with patch.dict("os.environ", {}, clear=True):
            cfg = WorkerConfig()

        assert cfg.temporal.address == "localhost:7233"
        assert cfg.temporal.namespace == "default"
        assert cfg.log_level == "INFO"

    def test_env_override(self) -> None:
        env = {
            "PINKY_TEMPORAL__ADDRESS": "temporal.prod:7233",
            "PINKY_TEMPORAL__NAMESPACE": "pinky",
            "PINKY_LOG_LEVEL": "DEBUG",
        }
        with patch.dict("os.environ", env, clear=True):
            cfg = WorkerConfig()

        assert cfg.temporal.address == "temporal.prod:7233"
        assert cfg.temporal.namespace == "pinky"
        assert cfg.log_level == "DEBUG"


class TestGetSettings:
    def test_returns_singleton(self) -> None:
        from pinky_worker import config
        config._settings = None

        with patch.dict("os.environ", {}, clear=True):
            s1 = get_settings()
            s2 = get_settings()

        assert s1 is s2
        config._settings = None
