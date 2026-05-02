---
name: pod-health
kind: scanner
version: 1.0.0
resource_kinds: [Pod, Deployment, ReplicaSet]
api_groups: ["", "apps"]
scan_interval_seconds: 60
timeout_seconds: 30
---
# Pod Health Scanner

Checks for unhealthy pod states across the cluster.

## Checks

### crash-loop-backoff
- severity: high
- condition: containerStatuses[].state.waiting.reason == "CrashLoopBackOff"
- evidence: pod events, container logs (last 50 lines), restart count

### oom-killed
- severity: critical
- condition: containerStatuses[].lastState.terminated.reason == "OOMKilled"
- evidence: pod events, resource requests vs limits, node memory pressure

### excessive-restarts
- severity: medium
- condition: containerStatuses[].restartCount > 5 within last hour
- evidence: pod events, restart timeline

### image-pull-error
- severity: high
- condition: containerStatuses[].state.waiting.reason in ("ImagePullBackOff", "ErrImagePull")
- evidence: pod events, image name, registry connectivity

### pending-too-long
- severity: medium
- condition: pod phase == "Pending" for > 5 minutes
- evidence: pod events, node scheduling conditions, resource quotas
