"""Eval graders for remediation step quality — resource kinds and consistency."""

import pytest

from evals.graders import assert_valid_resource_kinds, assert_consistent_kinds


GOOD_OUTPUT = """## Analysis

The pod is crashing due to nginx trying to bind to port 80 as non-root.

```json
{
  "summary": "Nginx crashes because restricted-v2 SCC prevents binding to port 80",
  "root_cause": "Container runs as non-root but nginx:latest binds to privileged port 80",
  "recommended_action": "Switch to nginx-unprivileged image",
  "confidence": 0.9,
  "remediation_steps": [
    {
      "action": "patch",
      "resource_kind": "rollout",
      "resource_name": "demo-rollout",
      "resource_namespace": "guestbook",
      "description": "Update image to nginx-unprivileged",
      "params": {"patch": {"spec": {"template": {"spec": {"containers": [{"name": "app", "image": "nginxinc/nginx-unprivileged:latest"}]}}}}},
      "risk": "low"
    }
  ],
  "manual_commands": [],
  "verification": {"check_delay_seconds": 30, "success_criteria": "pod running"}
}
```
"""

BAD_OUTPUT_WRONG_KIND = """## Analysis

Fix the deployment.

```json
{
  "summary": "Fix",
  "root_cause": "SCC",
  "recommended_action": "Patch",
  "confidence": 0.8,
  "remediation_steps": [
    {
      "action": "patch",
      "resource_kind": "deployment",
      "resource_name": "demo-rollout",
      "resource_namespace": "guestbook",
      "description": "Patch deployment",
      "params": {},
      "risk": "low"
    }
  ],
  "manual_commands": [],
  "verification": {}
}
```
"""

BAD_OUTPUT_UNKNOWN_KIND = """## Analysis

Patch the argoworkflow.

```json
{
  "summary": "Fix",
  "root_cause": "Error",
  "recommended_action": "Patch",
  "confidence": 0.7,
  "remediation_steps": [
    {
      "action": "patch",
      "resource_kind": "argoworkflow",
      "resource_name": "my-workflow",
      "resource_namespace": "default",
      "description": "Patch workflow",
      "params": {},
      "risk": "medium"
    }
  ],
  "manual_commands": [],
  "verification": {}
}
```
"""


def test_valid_resource_kinds_passes_for_known_kinds():
    failures = assert_valid_resource_kinds(GOOD_OUTPUT)
    assert len(failures) == 0


def test_valid_resource_kinds_flags_unknown_kind():
    failures = assert_valid_resource_kinds(BAD_OUTPUT_UNKNOWN_KIND)
    assert len(failures) == 1
    assert "argoworkflow" in failures[0]


def test_consistent_kinds_passes_when_matching():
    failures = assert_consistent_kinds(GOOD_OUTPUT, evidence_kind="rollout")
    assert len(failures) == 0


def test_consistent_kinds_flags_deployment_for_rollout():
    failures = assert_consistent_kinds(BAD_OUTPUT_WRONG_KIND, evidence_kind="rollout")
    assert len(failures) == 1
    assert "deployment" in failures[0]
    assert "rollout" in failures[0]


def test_consistent_kinds_ignores_non_default_kinds():
    failures = assert_consistent_kinds(BAD_OUTPUT_UNKNOWN_KIND, evidence_kind="rollout")
    assert len(failures) == 0


def test_no_json_block_returns_empty():
    failures = assert_valid_resource_kinds("No JSON here")
    assert len(failures) == 0
    failures = assert_consistent_kinds("No JSON here", evidence_kind="rollout")
    assert len(failures) == 0
