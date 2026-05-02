from datetime import datetime, timedelta, timezone

from pinky_worker.issues.correlator import IssueCorrelator, RawObservation


def _make_obs(
    fingerprint: str = "fp1",
    correlation_key: str = "ck1",
    title: str = "test issue",
    observed_at: datetime | None = None,
) -> RawObservation:
    return RawObservation(
        cluster_id="c1",
        scanner="pod-health",
        scanner_version="1.0.0",
        check_id="oom-killed",
        severity="critical",
        resource_kind="Pod",
        resource_namespace="ns1",
        resource_name="app-pod",
        title=title,
        fingerprint=fingerprint,
        correlation_key=correlation_key,
        observed_at=observed_at or datetime.now(timezone.utc),
    )


def test_first_observation_creates_issue() -> None:
    c = IssueCorrelator()
    result = c.correlate(_make_obs())
    assert result.action == "created"
    assert result.issue_id == "ck1"


def test_same_correlation_key_attaches() -> None:
    c = IssueCorrelator()
    c.correlate(_make_obs(fingerprint="fp1"))
    result = c.correlate(_make_obs(fingerprint="fp2", correlation_key="ck1"))
    assert result.action == "attached"


def test_same_fingerprint_deduplicates() -> None:
    c = IssueCorrelator()
    c.correlate(_make_obs(fingerprint="fp1"))
    result = c.correlate(_make_obs(fingerprint="fp1"))
    assert result.action == "deduplicated"


def test_resolved_issue_reopens_within_window() -> None:
    c = IssueCorrelator()
    c.correlate(_make_obs())
    c._issues["ck1"]["status"] = "resolved"
    c._issues["ck1"]["resolved_at"] = datetime.now(timezone.utc) - timedelta(minutes=30)

    result = c.correlate(_make_obs(fingerprint="fp_new"))
    assert result.action == "reopened"


def test_resolved_issue_creates_new_after_window() -> None:
    c = IssueCorrelator()
    c.correlate(_make_obs(correlation_key="ck_old"))
    c._issues["ck_old"]["status"] = "resolved"
    c._issues["ck_old"]["resolved_at"] = datetime.now(timezone.utc) - timedelta(hours=2)

    result = c.correlate(_make_obs(fingerprint="fp_new2", correlation_key="ck_new"))
    assert result.action == "created"


def test_different_correlation_keys_create_separate_issues() -> None:
    c = IssueCorrelator()
    r1 = c.correlate(_make_obs(fingerprint="fp1", correlation_key="ck1"))
    r2 = c.correlate(_make_obs(fingerprint="fp2", correlation_key="ck2"))
    assert r1.action == "created"
    assert r2.action == "created"
    assert r1.issue_id != r2.issue_id
