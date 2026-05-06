"""Tests for investigation prompt construction.

Verifies that run_investigation builds the correct LLM prompt
based on issue context, skill body, and evidence.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pinky_worker.execution.activities import (
    EvidenceBundle,
    _GENERIC_SKILL_BODY,
    _MAX_EVIDENCE_CHARS,
    _PROMPT_VERSION,
    run_investigation,
)


def _make_evidence(
    issue_title: str = "",
    resource_namespace: str = "",
    resource_name: str = "",
    resource_kind: str = "pod",
    sections: dict | None = None,
) -> EvidenceBundle:
    return EvidenceBundle(
        issue_id="issue-1",
        cluster_id="cluster-1",
        fingerprint="fp",
        evidence_hash="hash-1",
        sections=sections or {"pods": "[]", "events": "[]"},
        issue_title=issue_title,
        resource_namespace=resource_namespace,
        resource_name=resource_name,
        resource_kind=resource_kind,
    )


def _mock_llm_response(content: str = '```json\n{"summary": "test"}\n```'):
    response = MagicMock()
    response.content = content
    return response


@pytest.fixture
def mock_llm():
    router = MagicMock()
    router.complete = AsyncMock(return_value=_mock_llm_response())
    router_cls = MagicMock(return_value=router)
    with (
        patch("pinky_worker.llm.provider.LLMRouter", router_cls),
        patch("pinky_worker.llm.vertex_provider.VertexProvider"),
        patch("pinky_worker.llm.redaction.redact_evidence_sections", side_effect=lambda x: x),
        patch("temporalio.activity.heartbeat"),
    ):
        yield router


@pytest.mark.asyncio
async def test_prompt_includes_issue_context(mock_llm):
    evidence = _make_evidence(
        issue_title="Pod pinky/pinky-api has no resource limits",
        resource_namespace="pinky",
        resource_name="pinky-api",
        resource_kind="Pod",
    )

    await run_investigation(evidence, "check resource limits")

    call_args = mock_llm.complete.call_args[0][0]
    system_msg = call_args.messages[0]["content"]
    assert "SPECIFIC issue" in system_msg
    assert "Pod pinky/pinky-api has no resource limits" in system_msg
    assert "Pod/pinky/pinky-api" in system_msg
    assert "Focus ONLY on this resource" in system_msg


@pytest.mark.asyncio
async def test_prompt_omits_issue_context_when_no_title(mock_llm):
    evidence = _make_evidence()

    await run_investigation(evidence, "generic skill")

    call_args = mock_llm.complete.call_args[0][0]
    system_msg = call_args.messages[0]["content"]
    assert "SPECIFIC issue" not in system_msg


@pytest.mark.asyncio
async def test_generic_fallback_when_skill_empty(mock_llm):
    evidence = _make_evidence(issue_title="Some issue")

    await run_investigation(evidence, "")

    call_args = mock_llm.complete.call_args[0][0]
    user_msg = call_args.messages[1]["content"]
    assert _GENERIC_SKILL_BODY in user_msg


@pytest.mark.asyncio
async def test_skill_body_used_when_provided(mock_llm):
    evidence = _make_evidence(issue_title="Some issue")
    skill = "Check for OOMKilled containers and recommend memory increases."

    await run_investigation(evidence, skill)

    call_args = mock_llm.complete.call_args[0][0]
    user_msg = call_args.messages[1]["content"]
    assert skill in user_msg
    assert _GENERIC_SKILL_BODY not in user_msg


@pytest.mark.asyncio
async def test_evidence_truncated_when_too_long(mock_llm):
    big_sections = {"data": "x" * (_MAX_EVIDENCE_CHARS + 5000)}
    evidence = _make_evidence(sections=big_sections)

    await run_investigation(evidence, "check stuff")

    call_args = mock_llm.complete.call_args[0][0]
    user_msg = call_args.messages[1]["content"]
    assert "[evidence truncated]" in user_msg


@pytest.mark.asyncio
async def test_artifact_includes_prompt_metadata(mock_llm):
    evidence = _make_evidence(issue_title="Pod issue")
    skill = "Diagnose crashloop"

    result = await run_investigation(evidence, skill)

    assert "The Brain" in result.system_prompt
    assert "SPECIFIC issue" in result.system_prompt
    assert result.skill_used == skill
    assert result.prompt_version == _PROMPT_VERSION
