"""Eval test configuration — marks all evals with @pytest.mark.eval."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"
EXPECTATIONS_DIR = Path(__file__).parent / "expectations"


def pytest_collection_modifyitems(items: list) -> None:
    for item in items:
        item.add_marker(pytest.mark.eval)


def load_fixture(name: str) -> dict:
    path = FIXTURES_DIR / f"{name}.json"
    return json.loads(path.read_text())


def load_expectations(name: str) -> dict:
    import yaml

    path = EXPECTATIONS_DIR / f"{name}.yaml"
    return yaml.safe_load(path.read_text())
