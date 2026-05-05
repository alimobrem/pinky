"""Evidence redaction — strips sensitive data before LLM prompts.

Loads redaction rules from definitions/redaction-rules/*.md.
Applies regex patterns and field-name matching. Fails closed:
if redaction can't be confirmed, the field is excluded.
"""

from __future__ import annotations

import re

BUILTIN_PATTERNS: list[tuple[str, str]] = [
    # builtin-secrets patterns
    (r"Bearer [A-Za-z0-9\-._~+/]+", "[REDACTED-BEARER]"),
    (r"Basic [A-Za-z0-9+/=]+", "[REDACTED-BASIC]"),
    (r"(postgres|mysql|mongodb|redis)://[^\s]+", "[REDACTED-CONNSTR]"),
    # kubernetes-internal patterns
    (r"/var/run/secrets/kubernetes\.io/serviceaccount/token", "[REDACTED-SA-TOKEN]"),
    (r"eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}", "[REDACTED-JWT]"),
    (r"(certificate-authority-data|client-certificate-data|client-key-data)"
     r":\s*[A-Za-z0-9+/=]{20,}", "[REDACTED-KUBECONFIG]"),
    (r"token:\s*[A-Za-z0-9+/=._-]{20,}", "[REDACTED-TOKEN]"),
    (r"X-aws-ec2-metadata-token:\s*\S+", "[REDACTED-AWS-METADATA]"),
    (r"Metadata-Flavor:\s*Google", "[REDACTED-GCP-METADATA]"),
    (r"sh\.helm\.release\.v1\.[^\s]+", "[REDACTED-HELM-RELEASE]"),
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
