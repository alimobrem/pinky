---
name: suppress-resource-limits-low
kind: policy
version: 1.0.0
priority: 20
conditions:
  check_id_regex: "^(no-resource-limits|no-resource-requests)$"
  severity: low
action:
  type: suppress
  suppress_duration_minutes: 1440
---
# Suppress Low-Severity Resource Limit Findings

Missing resource requests (low severity) are informational — they don't
cause outages. Suppress for 24 hours to keep the task inbox focused
on actionable issues.

Medium-severity "no resource limits" findings still flow through the
normal policy pipeline (observe → investigate on recurrence).
