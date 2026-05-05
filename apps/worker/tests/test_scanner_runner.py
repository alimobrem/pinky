"""Tests for scanner_runner.py — now a thin shim re-exporting run_generic_checks."""

from pinky_worker.observation.generic_scanner import (
    run_generic_checks as original_run_generic_checks,
)
from pinky_worker.observation.scanner_runner import run_generic_checks


def test_reexport_is_same_function() -> None:
    assert run_generic_checks is original_run_generic_checks
