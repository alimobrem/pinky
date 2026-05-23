"""Chaos test fixtures. Requires running dev infrastructure (make dev-infra)."""

import pytest


def pytest_collection_modifyitems(items: list) -> None:
    for item in items:
        item.add_marker(pytest.mark.chaos)
