"""Tests for execution status state machine."""

from __future__ import annotations

import pytest

from pinky_worker.execution.state_machine import (
    TERMINAL_STATUSES,
    VALID_EXECUTION_TRANSITIONS,
    InvalidTransitionError,
    validate_transition,
)


class TestValidTransitions:
    def test_pending_to_running(self) -> None:
        validate_transition("pending", "running")

    def test_pending_to_failed(self) -> None:
        validate_transition("pending", "failed")

    def test_pending_to_cancelled(self) -> None:
        validate_transition("pending", "cancelled")

    def test_running_to_waiting_for_approval(self) -> None:
        validate_transition("running", "waiting_for_approval")

    def test_running_to_completed(self) -> None:
        validate_transition("running", "completed")

    def test_running_to_failed(self) -> None:
        validate_transition("running", "failed")

    def test_running_to_cancelled(self) -> None:
        validate_transition("running", "cancelled")

    def test_waiting_to_running(self) -> None:
        validate_transition("waiting_for_approval", "running")

    def test_waiting_to_failed(self) -> None:
        validate_transition("waiting_for_approval", "failed")

    def test_waiting_to_timed_out(self) -> None:
        validate_transition("waiting_for_approval", "timed_out")

    def test_waiting_to_cancelled(self) -> None:
        validate_transition("waiting_for_approval", "cancelled")


class TestInvalidTransitions:
    def test_completed_to_running(self) -> None:
        with pytest.raises(InvalidTransitionError):
            validate_transition("completed", "running")

    def test_failed_to_running(self) -> None:
        with pytest.raises(InvalidTransitionError):
            validate_transition("failed", "running")

    def test_pending_to_completed(self) -> None:
        with pytest.raises(InvalidTransitionError):
            validate_transition("pending", "completed")

    def test_pending_to_waiting(self) -> None:
        with pytest.raises(InvalidTransitionError):
            validate_transition("pending", "waiting_for_approval")

    def test_waiting_to_completed(self) -> None:
        with pytest.raises(InvalidTransitionError):
            validate_transition("waiting_for_approval", "completed")

    def test_cancelled_to_anything(self) -> None:
        for target in ("pending", "running", "completed", "failed"):
            with pytest.raises(InvalidTransitionError):
                validate_transition("cancelled", target)

    def test_timed_out_to_anything(self) -> None:
        for target in ("pending", "running", "completed"):
            with pytest.raises(InvalidTransitionError):
                validate_transition("timed_out", target)


class TestTerminalStatuses:
    def test_terminal_statuses_have_no_outgoing(self) -> None:
        for status in TERMINAL_STATUSES:
            assert VALID_EXECUTION_TRANSITIONS[status] == set()

    def test_every_non_terminal_has_path_to_terminal(self) -> None:
        for status, targets in VALID_EXECUTION_TRANSITIONS.items():
            if status not in TERMINAL_STATUSES:
                assert targets & TERMINAL_STATUSES, f"{status} has no path to terminal"

    def test_error_message_includes_both_statuses(self) -> None:
        with pytest.raises(InvalidTransitionError, match="completed.*running"):
            validate_transition("completed", "running")
