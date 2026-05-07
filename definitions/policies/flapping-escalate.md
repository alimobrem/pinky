---
name: flapping-escalate
kind: policy
version: 1.0.0
priority: 5
conditions:
  reopen_count_gte: 3
action:
  type: investigate
  risk_class: high
---
# Flapping Issue Escalation

Escalates issues that have been resolved and reopened 3 or more times
in 24 hours. Flapping indicates an underlying root cause that automated
resolution is not addressing. Requires deeper investigation.
