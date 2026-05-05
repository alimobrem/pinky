---
name: crashloop-investigate
kind: policy
version: 1.0.0
priority: 15
conditions:
  scanner: pod-health
  check_id: crash-loop-backoff
action:
  type: investigate
  skill: investigate-crashloop
  risk_class: high
---
# CrashLoopBackOff Investigation

CrashLoopBackOff always triggers investigation using the crashloop skill.
Checks previous container logs, deployment rollout history, and probe
configuration to determine root cause.
