---
name: investigate-crashloop
kind: skill
version: 1.0.0
description: Investigate CrashLoopBackOff containers
tools: [kubectl-get, kubectl-describe, kubectl-logs, kubectl-events]
model_tier: reasoning
timeout_seconds: 120
---
# Investigate CrashLoopBackOff

When investigating a CrashLoopBackOff:

1. Get pod description with `kubectl-describe` to see current state, conditions, and events
2. Get previous container logs with `kubectl-logs` (set `previous: true`) — the crash output is in the terminated container
3. Get events for the pod with `kubectl-events` to see scheduling, pulling, and lifecycle events
4. Check the deployment/replicaset with `kubectl-get` to see if this is a rollout issue

## Root cause categories

### Application error
- Exit code 1: application-level error (check logs for stack trace)
- Exit code 137: killed by signal (likely OOM — escalate to investigate-oom)
- Exit code 139: segfault (binary compatibility issue or corrupted image)

### Configuration error
- Missing environment variables or config files
- Invalid command or entrypoint
- Missing secrets or configmaps (check event: "MountVolume.SetUp failed")

### Resource issue
- Liveness probe failing (check probe config vs actual startup time)
- Readiness probe timing out (under-provisioned or slow startup)
- Resource limits too low (check requests vs limits vs actual usage)

### Deployment issue
- Recent rollout caused the crash (check `kubectl-rollout history`)
- Image tag changed to broken version
- Init container failing

## Recommendation framework

- If caused by recent rollout → recommend rollback to last known-good revision
- If probe misconfiguration → recommend probe adjustment with specific values
- If missing config/secret → recommend creating the missing resource
- If resource limits → recommend limit increase with specific values based on actual usage
- If application bug → recommend rollback + escalation to application team
