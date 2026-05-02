---
name: critical-investigate
kind: policy
version: 1.0.0
priority: 10
conditions:
  severity_gte: critical
action:
  type: investigate
---
# Critical Severity Investigation Policy

All critical-severity observations trigger an immediate investigation by The Brain.
No waiting for recurrence threshold.
