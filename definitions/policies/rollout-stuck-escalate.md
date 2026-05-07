---
name: rollout-stuck-escalate
kind: policy
version: 1.0.0
priority: 16
conditions:
  check_id: rollout-stalled
  recurrence_count_gte: 10
action:
  type: investigate
  risk_class: high
---
# Rollout Stuck Escalation

Escalates a stalled deployment rollout to investigation after 10
consecutive observations (roughly 10 minutes at 1-minute scan interval).
A rollout stuck this long likely needs manual intervention.
