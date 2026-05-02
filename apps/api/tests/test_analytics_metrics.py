from pinky_api.analytics.metrics import (
    OutcomeRecord,
    ScannerQuality,
    compute_automation_success_rate,
    compute_confidence_calibration,
    compute_override_rate,
    compute_recurrence_rate,
    compute_scanner_noise_ratio,
)


def _outcome(outcome: str = "verified_fixed", confidence: float = 0.9) -> OutcomeRecord:
    return OutcomeRecord(
        execution_id="e1",
        outcome=outcome,
        cluster_id="c1",
        scanner="pod-health",
        confidence=confidence,
        recorded_at="2026-05-01T00:00:00Z",
    )


def test_automation_success_rate() -> None:
    outcomes = [_outcome("verified_fixed"), _outcome("verified_fixed"), _outcome("recurred")]
    rate = compute_automation_success_rate(outcomes)
    assert rate is not None
    assert abs(rate - 2 / 3) < 0.01


def test_automation_success_rate_empty() -> None:
    assert compute_automation_success_rate([]) is None


def test_recurrence_rate() -> None:
    outcomes = [_outcome("verified_fixed")] * 8 + [_outcome("recurred")] * 2
    rate = compute_recurrence_rate(outcomes)
    assert rate is not None
    assert abs(rate - 0.2) < 0.01


def test_override_rate() -> None:
    outcomes = [_outcome("verified_fixed")] * 9 + [_outcome("operator_overridden")]
    rate = compute_override_rate(outcomes)
    assert rate is not None
    assert abs(rate - 0.1) < 0.01


def test_scanner_noise_ratio() -> None:
    scanner = ScannerQuality(scanner_name="pod-health", signal_total=100, signal_suppressed=30)
    ratio = compute_scanner_noise_ratio(scanner)
    assert ratio is not None
    assert abs(ratio - 0.3) < 0.01


def test_scanner_noise_ratio_zero_signals() -> None:
    scanner = ScannerQuality(scanner_name="empty", signal_total=0)
    assert compute_scanner_noise_ratio(scanner) is None


def test_confidence_calibration() -> None:
    outcomes = [
        _outcome("verified_fixed", confidence=0.9),
        _outcome("verified_fixed", confidence=0.85),
        _outcome("recurred", confidence=0.9),
        _outcome("verified_fixed", confidence=0.5),
        _outcome("recurred", confidence=0.4),
    ]
    cal = compute_confidence_calibration(outcomes, buckets=5)
    assert "0.8-1.0" in cal
    assert "0.4-0.6" in cal


def test_confidence_calibration_empty() -> None:
    assert compute_confidence_calibration([]) == {}
