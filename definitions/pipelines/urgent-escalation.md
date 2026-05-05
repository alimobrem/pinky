---
name: urgent-escalation
kind: pipeline
version: 1.0.0
trigger: policy_decision
conditions:
  action_type: investigate
  risk_class: critical
---
# Urgent Escalation Pipeline

Runs after the policy engine assigns a critical risk class to an investigation.

## Steps

1. **Fast-track investigation** — skip the 2-consecutive-scan-cycle wait, investigate immediately
2. **Notify** — emit domain event `investigation.urgent_started` for webhook delivery (Slack/Teams)
3. **Set task priority** — if investigation creates a task, set priority to `critical`
4. **Auto-assign** — if an on-call binding exists for the cluster, auto-assign the task to the on-call operator
5. **Track SLA** — start SLA timer (30min to acknowledge, 4hr to resolve)
