"""Issue correlator — groups observations into durable issues.

Rules:
1. Same fingerprint for same cluster+scanner: upsert observation
2. Same correlation key as open issue: attach to existing issue
3. Same correlation key as recently resolved issue (<1hr): reopen
4. Identical fingerprint within scan interval: collapse to latest
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone


@dataclass
class RawObservation:
    cluster_id: str
    scanner: str
    scanner_version: str
    check_id: str
    severity: str
    resource_kind: str
    resource_namespace: str
    resource_name: str
    title: str
    payload: dict = field(default_factory=dict)
    observed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    fingerprint: str = ""
    correlation_key: str = ""


@dataclass
class CorrelationResult:
    action: str  # "created" | "attached" | "reopened" | "deduplicated"
    issue_id: str | None = None
    observation_id: str | None = None


REOPEN_WINDOW = timedelta(hours=1)


class IssueCorrelator:
    """In-memory correlator for testing. Production uses Postgres."""

    def __init__(self) -> None:
        self._issues: dict[str, dict] = {}
        self._observations: dict[str, dict] = {}

    def correlate(self, obs: RawObservation) -> CorrelationResult:
        # Check for duplicate fingerprint within recent window
        if obs.fingerprint in self._observations:
            existing = self._observations[obs.fingerprint]
            existing["observed_at"] = obs.observed_at
            existing["payload"] = obs.payload
            return CorrelationResult(action="deduplicated", observation_id=obs.fingerprint)

        self._observations[obs.fingerprint] = {
            "fingerprint": obs.fingerprint,
            "observed_at": obs.observed_at,
            "payload": obs.payload,
        }

        # Check for existing open issue with same correlation key
        if obs.correlation_key in self._issues:
            issue = self._issues[obs.correlation_key]
            if issue["status"] == "open":
                issue["last_seen_at"] = obs.observed_at
                return CorrelationResult(action="attached", issue_id=obs.correlation_key)

            # Check if recently resolved — reopen
            resolved_at = issue.get("resolved_at")
            if resolved_at and (obs.observed_at - resolved_at) < REOPEN_WINDOW:
                issue["status"] = "open"
                issue["resolved_at"] = None
                issue["last_seen_at"] = obs.observed_at
                return CorrelationResult(action="reopened", issue_id=obs.correlation_key)

        # Create new issue
        self._issues[obs.correlation_key] = {
            "correlation_key": obs.correlation_key,
            "title": obs.title,
            "severity": obs.severity,
            "status": "open",
            "first_seen_at": obs.observed_at,
            "last_seen_at": obs.observed_at,
            "resolved_at": None,
            "cluster_id": obs.cluster_id,
        }
        return CorrelationResult(action="created", issue_id=obs.correlation_key)
