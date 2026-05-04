"""ROI and quality metric computation.

All metrics are computed from the analytics_events table.
These are the numbers that prove Pinky's value.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ROIMetrics:
    period_start: str
    period_end: str
    signal_to_task_p50_seconds: float | None = None
    signal_to_task_p95_seconds: float | None = None
    issues_resolved_total: int = 0
    issues_resolved_auto: int = 0
    issues_resolved_assisted: int = 0
    automation_success_rate: float | None = None
    cost_per_resolution_tokens: float | None = None
    operator_override_rate: float | None = None
    approval_turnaround_p50_seconds: float | None = None
    recurrence_rate_7d: float | None = None
    confidence_calibration: dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True)
class ScannerQuality:
    scanner_name: str
    signal_total: int = 0
    signal_suppressed: int = 0
    signal_escalated: int = 0
    signal_tasked: int = 0
    false_positive_rate: float | None = None
    noise_ratio: float | None = None


@dataclass(frozen=True)
class OutcomeRecord:
    execution_id: str
    outcome: str  # verified_fixed, recurred, operator_overridden, rolled_back, dismissed
    cluster_id: str
    scanner: str
    confidence: float
    recorded_at: str


OUTCOME_TYPES = {
    "verified_fixed",
    "recurred",
    "operator_overridden",
    "rolled_back",
    "dismissed",
}


def compute_automation_success_rate(outcomes: list[OutcomeRecord]) -> float | None:
    if not outcomes:
        return None
    verified = sum(1 for o in outcomes if o.outcome == "verified_fixed")
    return verified / len(outcomes)


def compute_recurrence_rate(outcomes: list[OutcomeRecord]) -> float | None:
    if not outcomes:
        return None
    recurred = sum(1 for o in outcomes if o.outcome == "recurred")
    return recurred / len(outcomes)


def compute_override_rate(outcomes: list[OutcomeRecord]) -> float | None:
    if not outcomes:
        return None
    overridden = sum(1 for o in outcomes if o.outcome == "operator_overridden")
    return overridden / len(outcomes)


def compute_scanner_noise_ratio(scanner: ScannerQuality) -> float | None:
    if scanner.signal_total == 0:
        return None
    return scanner.signal_suppressed / scanner.signal_total


def compute_confidence_calibration(outcomes: list[OutcomeRecord], buckets: int = 5) -> dict[str, float]:
    if not outcomes:
        return {}

    bucket_size = 1.0 / buckets
    calibration: dict[str, float] = {}

    for i in range(buckets):
        lower = i * bucket_size
        upper = (i + 1) * bucket_size
        label = f"{lower:.1f}-{upper:.1f}"

        in_bucket = [o for o in outcomes if lower <= o.confidence < upper]
        if not in_bucket:
            continue

        correct = sum(1 for o in in_bucket if o.outcome == "verified_fixed")
        calibration[label] = correct / len(in_bucket)

    return calibration
