"""Execution status state machine — single source of truth for valid transitions."""

VALID_EXECUTION_TRANSITIONS: dict[str, set[str]] = {
    "pending": {"running", "failed", "cancelled"},
    "running": {"waiting_for_approval", "completed", "failed", "cancelled"},
    "waiting_for_approval": {"running", "failed", "timed_out", "cancelled"},
    "completed": set(),
    "failed": set(),
    "cancelled": set(),
    "timed_out": set(),
}

TERMINAL_STATUSES = frozenset({"completed", "failed", "cancelled", "timed_out"})


class InvalidTransitionError(ValueError):
    def __init__(self, current: str, target: str) -> None:
        self.current = current
        self.target = target
        super().__init__(f"execution transition {current!r} -> {target!r} is not allowed")


def validate_transition(current: str, target: str) -> None:
    allowed = VALID_EXECUTION_TRANSITIONS.get(current, set())
    if target not in allowed:
        raise InvalidTransitionError(current, target)
