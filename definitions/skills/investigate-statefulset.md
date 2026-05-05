---
name: investigate-statefulset
kind: skill
version: 1.0.0
description: Investigate StatefulSet rollout and availability issues
tools: [kubectl-get, kubectl-describe, kubectl-events, kubectl-logs]
model_tier: reasoning
timeout_seconds: 120
---
# Investigate StatefulSet Issues

StatefulSets have ordered startup/shutdown. A stuck ordinal blocks everything after it.

1. Get StatefulSet description with `kubectl-describe` — check updateStrategy, partition, revision
2. Get pod status per ordinal with `kubectl-get` — which ordinal is stuck?
3. Get events for the stuck pod with `kubectl-events`
4. Get logs from the stuck pod with `kubectl-logs` (previous=true if restarting)
5. Check PVC status per ordinal — is a volume mount failing?

## Root cause categories

### Stuck ordinal
- Pod at ordinal N failing readiness/liveness (check probes)
- PVC for ordinal N is Pending (storage class issue, capacity)
- Init container failing (check init container logs)

### Rollout stuck
- Partition set too high (intentional canary or mistake)
- updateRevision != currentRevision but no pods updating
- OnDelete strategy requires manual pod deletion

### Data issue
- PVC data corruption causing crash on startup
- Incompatible schema migration in new version

## Recommendation framework

- If stuck ordinal has failing probe → recommend probe adjustment or image fix
- If PVC pending → recommend storage class or capacity fix
- If partition set → check if intentional canary, recommend completing rollout
- If data issue → recommend rollback + data recovery plan
