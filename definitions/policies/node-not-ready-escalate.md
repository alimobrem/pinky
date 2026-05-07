---
name: node-not-ready-escalate
kind: policy
version: 1.0.0
priority: 12
conditions:
  check_id: not-ready
  resource_kind: Node
  recurrence_count_gte: 5
action:
  type: investigate
  risk_class: critical
---
# Node Not Ready Escalation

Escalates a NotReady node to investigation after 5 consecutive
observations (roughly 5 minutes). A node stuck in NotReady impacts all
pods scheduled on it and may indicate hardware, network, or kubelet
issues.
