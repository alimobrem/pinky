---
name: high-recurring-investigate
kind: policy
version: 1.0.0
priority: 20
conditions:
  severity_gte: high
  recurrence_count_gte: 3
action:
  type: investigate
---
# High Severity Recurring Investigation

High-severity observations that recur 3+ times trigger a Brain investigation.
Single occurrences stay in Watch to avoid wasting LLM calls on transient blips.
