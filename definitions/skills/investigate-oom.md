---
name: investigate-oom
kind: skill
version: 1.0.0
description: Investigate OOM kills on a cluster
tools: [kubectl-get, kubectl-describe, kubectl-logs, kubectl-top, kubectl-events, prometheus-query]
model_tier: reasoning
timeout_seconds: 120
---
# Investigate OOM Kills

When investigating OOM kills:

1. Get pod events and container status with `kubectl-describe`
2. Check resource requests vs limits — are limits set? Are they realistic?
3. Check restart count and timeline — is this a new issue or recurring?
4. Check node-level memory pressure
5. Look for memory leak patterns (steadily increasing RSS over time)

## Recommendation framework

- If limits are too low relative to actual usage → recommend increasing limits
- If no HPA exists and usage is variable → recommend adding HPA with memory target
- If usage grows unbounded over time → flag as potential memory leak, recommend profiling
- If node is under memory pressure → recommend node scaling or pod anti-affinity
- If multiple pods on same node are OOM → investigate node-level issue first

## Key PromQL queries

- **Memory usage trend (24h):** `container_memory_working_set_bytes{namespace="NS",pod=~"POD.*"}`
- **Memory vs limit:** `container_memory_working_set_bytes / on(pod,container) kube_pod_container_resource_limits{resource="memory"}`
- **OOM kill count:** `kube_pod_container_status_last_terminated_reason{reason="OOMKilled",namespace="NS"}`
- **Memory P95 (sizing):** `quantile_over_time(0.95, container_memory_working_set_bytes{namespace="NS",pod=~"POD.*"}[24h:])`
