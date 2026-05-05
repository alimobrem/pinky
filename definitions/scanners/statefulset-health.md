---
name: statefulset-health
kind: scanner
version: 1.0.0
resource_kinds: [StatefulSet]
api_groups: [apps]
scan_interval_seconds: 60
timeout_seconds: 30
---
# StatefulSet Health Scanner

Checks for unhealthy StatefulSet states. StatefulSets have ordered
startup/shutdown semantics — a stuck ordinal blocks the entire rollout.

## Checks

### sts-rollout-stuck
- severity: high
- condition: status.updatedReplicas < spec.replicas AND status.currentRevision != status.updateRevision for > 5 minutes
- evidence: StatefulSet status, pod statuses per ordinal, events

### sts-replicas-unavailable
- severity: high
- condition: status.readyReplicas < spec.replicas for > 5 minutes
- evidence: StatefulSet status, pod events, PVC status per ordinal

### sts-ordinal-stuck
- severity: critical
- condition: pod at ordinal N is not Ready while ordinals 0..N-1 are Ready, blocking rollout
- evidence: per-ordinal pod status, events, PVC bindings
