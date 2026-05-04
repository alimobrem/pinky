"""Redaction completeness tests — plant known secrets, verify they're removed."""

from __future__ import annotations

from evals.graders import assert_redaction_clean
from pinky_worker.llm.redaction import redact_evidence_sections, redact_text


def test_bearer_token_redacted() -> None:
    text = "Authorization: Bearer eyJhbGciOiJSUzI1NiJ9.payload.signature"
    result = redact_text(text)
    failures = assert_redaction_clean(result)
    assert failures == [], f"Bearer token survived redaction: {failures}"


def test_basic_auth_redacted() -> None:
    text = "Authorization: Basic dXNlcjpwYXNzd29yZA=="
    result = redact_text(text)
    failures = assert_redaction_clean(result)
    assert failures == [], f"Basic auth survived redaction: {failures}"


def test_connection_string_redacted() -> None:
    text = "DATABASE_URL=postgres://admin:s3cr3t@db.prod.internal:5432/myapp"
    result = redact_text(text)
    failures = assert_redaction_clean(result)
    assert failures == [], f"Connection string survived redaction: {failures}"


def test_evidence_sections_bearer_redacted() -> None:
    sections = {
        "events": '[{"message": "Bearer eyJhbGciOiJIUzI1NiJ9.test.sig"}]',
        "cluster_id": "c1",
    }
    redacted = redact_evidence_sections(sections)
    failures = assert_redaction_clean(redacted["events"])
    assert failures == [], f"Bearer survived redaction: {failures}"


def test_evidence_sections_connection_string_redacted() -> None:
    sections = {
        "pods": '[{"env": [{"name": "DB_URL", "value": "postgres://admin:pw@host:5432/db"}]}]',
    }
    redacted = redact_evidence_sections(sections)
    failures = assert_redaction_clean(redacted["pods"])
    assert failures == [], f"Connection string survived: {failures}"


def test_sensitive_env_values_with_api_keys() -> None:
    sections = {
        "pods": '[{"env": [{"name": "API_KEY", "value": "sk-prod-abc123def456ghijklmnopqrst"}]}]',
    }
    redacted = redact_evidence_sections(sections)
    failures = assert_redaction_clean(redacted["pods"])
    assert failures == [], f"API key survived: {failures}"


def test_bearer_and_connection_string_together() -> None:
    text = "Token: Bearer abc123def456 and connection postgres://root:pass@host:5432/db"
    result = redact_text(text)
    assert "Bearer abc123" not in result
    assert "postgres://root:pass" not in result
