---
name: investigate-resource-limits
kind: skill
version: 1.0.0
description: Investigate missing resource limits using Prometheus metrics
tools: [prometheus-query, kubectl-describe]
model_tier: reasoning
timeout_seconds: 120
---
# Investigate Missing Resource Limits

When a pod or deployment has no resource limits or requests, determine
appropriate values based on **actual observed usage from Prometheus**, not
generic defaults.

## Key PromQL Queries

Use these to derive right-sized values:

- **CPU P95 (5m rate, last 24h):** `quantile_over_time(0.95, rate(container_cpu_usage_seconds_total{namespace="NS",pod=~"POD.*"}[5m])[24h:])`
- **CPU P50:** same with `0.50`
- **Memory P95 (last 24h):** `quantile_over_time(0.95, container_memory_working_set_bytes{namespace="NS",pod=~"POD.*"}[24h:])`
- **Memory P50:** same with `0.50`
- **OOM kill history:** `kube_pod_container_status_last_terminated_reason{reason="OOMKilled",namespace="NS",pod=~"POD.*"}`

## Recommendation Guidelines

- **requests** = P50 observed usage (steady-state baseline)
- **limits** = 2x P95 observed usage (headroom for spikes)
- If Prometheus is unavailable, say so — do NOT invent numbers
- Show the raw metric values alongside the recommendation
- Include all containers (init + app)
- CPU in millicores, memory in MiB
- Provide a ready-to-run `oc patch` command with the derived values
