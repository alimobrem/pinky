---
name: oom-investigate
kind: policy
version: 1.0.0
priority: 15
conditions:
  scanner: pod-health
  check_id: oom-killed
action:
  type: investigate
  skill: investigate-oom
  risk_class: high
---
# OOM Kill Investigation

OOM kills always trigger investigation using the investigate-oom skill.
OOM is already critical severity, but this rule ensures the right skill is
attached and the risk class is set for downstream approval gating.
