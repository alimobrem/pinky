---
name: medium-recurring-investigate
kind: policy
version: 1.0.0
priority: 100
conditions:
  severity_gte: medium
  recurrence_count_gte: 5
action:
  type: investigate
---
# Medium Severity Persistent Issue

Medium-severity observations that recur 5+ times are no longer transient.
Escalate to investigation — something is consistently wrong and the
operator should know about it.
