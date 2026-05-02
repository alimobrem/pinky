from pinky_worker.llm.redaction import (
    is_sensitive_env_name,
    redact_env_vars,
    redact_evidence_sections,
    redact_text,
)


def test_redact_bearer_token() -> None:
    text = "Authorization: Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.payload.signature"
    result = redact_text(text)
    assert "[REDACTED-BEARER]" in result
    assert "eyJ" not in result


def test_redact_basic_auth() -> None:
    text = "Authorization: Basic dXNlcjpwYXNzd29yZA=="
    result = redact_text(text)
    assert "[REDACTED-BASIC]" in result


def test_redact_connection_string() -> None:
    text = "url: postgres://admin:secret@db.host:5432/mydb"
    result = redact_text(text)
    assert "[REDACTED-CONNSTR]" in result
    assert "secret" not in result


def test_redact_preserves_normal_text() -> None:
    text = "Pod nginx-abc123 is in CrashLoopBackOff state"
    result = redact_text(text)
    assert result == text


def test_sensitive_env_names() -> None:
    assert is_sensitive_env_name("DATABASE_PASSWORD")
    assert is_sensitive_env_name("API_KEY")
    assert is_sensitive_env_name("OAUTH_TOKEN")
    assert is_sensitive_env_name("AWS_SECRET_ACCESS_KEY")
    assert not is_sensitive_env_name("LOG_LEVEL")
    assert not is_sensitive_env_name("PORT")


def test_redact_env_vars() -> None:
    envs = [
        {"name": "LOG_LEVEL", "value": "debug"},
        {"name": "DATABASE_PASSWORD", "value": "supersecret"},
        {"name": "API_KEY", "value": "sk-12345"},
    ]
    result = redact_env_vars(envs)
    assert result[0]["value"] == "debug"
    assert result[1]["value"] == "[REDACTED]"
    assert result[2]["value"] == "[REDACTED]"


def test_redact_evidence_sections() -> None:
    sections = {
        "status": "Pod running, auth: Bearer abc123token",
        "events": "Normal events, no secrets here",
    }
    result = redact_evidence_sections(sections)
    assert "[REDACTED-BEARER]" in result["status"]
    assert result["events"] == sections["events"]
