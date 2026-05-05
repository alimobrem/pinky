---
name: pending-pod-investigate
kind: policy
version: 1.0.0
priority: 30
conditions:
  scanner: pod-health
  check_id: pending-too-long
  recurrence_count_gte: 2
action:
  type: investigate
  skill: investigate-pending-pod
---
# Pending Pod Investigation

Pods stuck in Pending across 2+ scan cycles are likely a real scheduling
problem (insufficient resources, taint mismatch, PVC pending) rather than
transient scheduler delay.
