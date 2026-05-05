---
name: deployment-health
kind: scanner
version: 1.0.0
resource_kinds: [Deployment, ReplicaSet]
api_groups: [apps]
scan_interval_seconds: 60
timeout_seconds: 30
---
# Deployment Health Scanner

Checks for unhealthy deployment states.

## Checks

### rollout-stalled
- severity: high
- condition: status.conditions where type == "Progressing" and status == "False"
- evidence: deployment conditions, replica counts, rollout history

### replicas-unavailable
- severity: high
- condition: status.unavailableReplicas > 0 for > 5 minutes
- evidence: deployment status, pod statuses, events

### replica-mismatch
- severity: medium
- condition: status.readyReplicas < spec.replicas for > 5 minutes
- evidence: deployment spec vs status, pod events, scheduling constraints

### hpa-maxed-out
- severity: medium
- condition: HPA currentReplicas == maxReplicas and current CPU/memory > target
- evidence: HPA status, deployment resource usage, scaling history
