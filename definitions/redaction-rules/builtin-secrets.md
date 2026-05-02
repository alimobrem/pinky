---
name: builtin-secrets
kind: redaction-rule
version: 1.0.0
priority: 1
---
# Built-in Secret Redaction

Patterns to redact from all evidence before LLM prompt assembly.

## Environment variable names to redact values for
- names containing: SECRET, KEY, TOKEN, PASSWORD, CREDENTIAL, API_KEY, APIKEY

## Kubernetes resource fields to redact
- Secret resources: data.* and stringData.*
- ConfigMap: data entries matching sensitive name patterns above

## Generic patterns
- Bearer tokens: Bearer [A-Za-z0-9\-._~+/]+ → [REDACTED-BEARER]
- Basic auth: Basic [A-Za-z0-9+/=]+ → [REDACTED-BASIC]
- Connection strings: (postgres|mysql|mongodb|redis):\/\/[^\s]+ → [REDACTED-CONNSTR]

## Behavior
- Redaction failures must fail closed — if redaction cannot be confirmed, do not include the field in evidence
