---
name: daemonset-investigate
kind: policy
version: 1.0.0
priority: 20
conditions:
  scanner: daemonset-health
  severity_gte: high
action:
  type: investigate
  skill: investigate-daemonset
  risk_class: high
---
# DaemonSet Investigation

High-severity DaemonSet findings (unavailable pods) trigger investigation.
DaemonSets run logging, monitoring, and CNI — gaps affect observability
and connectivity for all workloads on affected nodes.
