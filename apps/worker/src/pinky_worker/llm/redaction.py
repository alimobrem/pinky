"""Evidence redaction — strips sensitive data before LLM prompts.

Loads redaction rules from definitions/redaction-rules/*.md.
Applies regex patterns and field-name matching. Fails closed:
if redaction can't be confirmed, the field is excluded.
"""

from __future__ import annotations

import re

BUILTIN_PATTERNS: list[tuple[str, str]] = [
    (r"Bearer [A-Za-z0-9\-._~+/]+", "[REDACTED-BEARER]"),
    (r"Basic [A-Za-z0-9+/=]+", "[REDACTED-BASIC]"),
    (r"(postgres|mysql|mongodb|redis)://[^\s]+", "[REDACTED-CONNSTR]"),
]

SENSITIVE_ENV_NAMES = {"SECRET", "KEY", "TOKEN", "PASSWORD", "CREDENTIAL", "API_KEY", "APIKEY"}


def is_sensitive_env_name(name: str) -> bool:
    upper = name.upper()
    return any(s in upper for s in SENSITIVE_ENV_NAMES)


def redact_text(text: str, extra_patterns: list[tuple[str, str]] | None = None) -> str:
    patterns = BUILTIN_PATTERNS + (extra_patterns or [])
    result = text
    for pattern, replacement in patterns:
        result = re.sub(pattern, replacement, result)
    return result


def redact_env_vars(env_list: list[dict]) -> list[dict]:
    redacted = []
    for env in env_list:
        name = env.get("name", "")
        if is_sensitive_env_name(name):
            redacted.append({"name": name, "value": "[REDACTED]"})
        else:
            redacted.append(env)
    return redacted


def redact_evidence_sections(sections: dict[str, str]) -> dict[str, str]:
    return {k: redact_text(v) for k, v in sections.items()}
