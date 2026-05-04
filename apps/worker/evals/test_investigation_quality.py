"""Investigation output quality tests using evidence fixtures.

These tests run deterministic graders against simulated LLM outputs.
Mark with @pytest.mark.eval for CI separation.

For live LLM evaluation, set PINKY_EVAL_LIVE=true and provide
ANTHROPIC_API_KEY or VERTEX credentials.
"""

from __future__ import annotations

import os

import pytest

from evals.conftest import load_expectations, load_fixture
from evals.graders import assert_redaction_clean, assert_relevance, assert_safety, assert_structure

FIXTURES = ["oom-kill-simple", "crashloop-config-error", "image-pull-error"]
LIVE = os.environ.get("PINKY_EVAL_LIVE", "false") == "true"


def _simulate_investigation(fixture: dict) -> str:
    """Simulate an LLM investigation response for testing graders.

    In live mode, this would call the actual LLM. For now, generates
    a structured response from the evidence to validate the grading pipeline.
    """
    sections = fixture["sections"]
    pods = sections.get("pods", "")
    events = sections.get("events", "")

    if "OOMKill" in pods or "OOMKill" in events:
        return (
            "## Summary\n"
            "The pod web-frontend-abc123 is in CrashLoopBackOff due to repeated OOMKilled events. "
            "The memory limit of 128Mi is insufficient for the workload.\n\n"
            "## Root Cause\n"
            "The container memory limit is set to 128Mi but the process requires more memory. "
            "The kernel OOM killer terminates the process when it exceeds the cgroup memory limit.\n\n"
            "## Recommendation\n"
            "Increase the memory limit to at least 256Mi-512Mi based on actual usage patterns. "
            "Monitor with `kubectl top pod` to determine the right value."
        )

    if "Cannot find module" in pods or "config" in events.lower():
        return (
            "## Summary\n"
            "The pod api-server-xyz789 is crashing because it cannot find the config file "
            "'/app/config/database.yaml'. This is a missing ConfigMap mount.\n\n"
            "## Root Cause\n"
            "The deployment references a config file at /app/config/database.yaml but the "
            "corresponding ConfigMap is not mounted. Check if the ConfigMap exists and is "
            "correctly referenced in the pod spec volumes.\n\n"
            "## Recommendation\n"
            "Create or fix the ConfigMap mount for the database.yaml config file. "
            "Verify the volume mount path matches the expected config location."
        )

    if "ImagePullBackOff" in pods or "pull access denied" in events:
        return (
            "## Summary\n"
            "The pod worker-deploy-qrs456 cannot pull image from registry.internal.corp. "
            "This is a registry authentication issue.\n\n"
            "## Root Cause\n"
            "The image pull failed because the registry requires authentication but no valid "
            "imagePullSecrets are configured. The error indicates 'pull access denied'.\n\n"
            "## Recommendation\n"
            "Create a registry credential secret and add it as an imagePullSecret to the "
            "pod spec or service account. Verify the secret has valid registry credentials."
        )

    return (
        "## Summary\nUnknown issue detected.\n\n"
        "## Root Cause\nInsufficient evidence.\n\n"
        "## Recommendation\nInvestigate manually."
    )


@pytest.mark.parametrize("fixture_name", FIXTURES)
def test_investigation_structure(fixture_name: str) -> None:
    fixture = load_fixture(fixture_name)
    output = _simulate_investigation(fixture)
    failures = assert_structure(output)
    assert failures == [], f"Structure failures: {failures}"


@pytest.mark.parametrize("fixture_name", FIXTURES)
def test_investigation_safety(fixture_name: str) -> None:
    fixture = load_fixture(fixture_name)
    output = _simulate_investigation(fixture)
    failures = assert_safety(output)
    assert failures == [], f"Safety failures: {failures}"


@pytest.mark.parametrize("fixture_name", FIXTURES)
def test_investigation_relevance(fixture_name: str) -> None:
    fixture = load_fixture(fixture_name)
    expectations = load_expectations(fixture_name)
    output = _simulate_investigation(fixture)
    failures = assert_relevance(output, expectations)
    assert failures == [], f"Relevance failures: {failures}"


@pytest.mark.parametrize("fixture_name", FIXTURES)
def test_evidence_redaction_clean(fixture_name: str) -> None:
    fixture = load_fixture(fixture_name)
    for section_name, section_text in fixture["sections"].items():
        failures = assert_redaction_clean(section_text)
        assert failures == [], f"Redaction failures in {section_name}: {failures}"
