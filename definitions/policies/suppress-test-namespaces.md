---
name: suppress-test-namespaces
kind: policy
version: 1.0.0
priority: 50
conditions:
  resource_namespace_regex: "^(test|qa|load-test|sandbox|dev-scratch)$"
action:
  type: suppress
  suppress_duration_minutes: 60
---
# Suppress Test Namespace Noise

Observations from test, QA, load-test, sandbox, and dev-scratch namespaces
are suppressed for 60 minutes. These namespaces are expected to have
transient failures during testing and should not generate tasks or
investigations.
