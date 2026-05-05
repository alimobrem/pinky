---
name: investigate-service-endpoints
kind: skill
version: 1.0.0
description: Investigate services with missing or degraded endpoints
tools: [kubectl-get, kubectl-describe, kubectl-events]
model_tier: utility
timeout_seconds: 60
---
# Investigate Service Endpoint Issues

1. Get service description with `kubectl-describe` — check selector, ports, type
2. Get pods matching the selector with `kubectl-get` — do any pods exist? Are they Ready?
3. Get endpoint slices with `kubectl-get` — what addresses are registered?
4. Get events in the namespace with `kubectl-events` — recent deployment or scaling changes

## Root cause categories

### Zero endpoints
- No pods match the service selector (label mismatch after deployment change)
- Pods exist but none are Ready (failing readiness probes)
- Deployment scaled to 0
- Namespace has no matching workload (service created before deployment)

### Partial endpoints
- Some pods failing readiness probes
- Rolling update in progress (transient)
- Node pressure causing evictions on some nodes
- Pod anti-affinity spreading pods to unhealthy nodes

## Recommendation framework

- If selector mismatch → recommend correcting labels on deployment or service
- If all pods not ready → escalate to pod health investigation
- If scaled to 0 → recommend scaling up or checking HPA
- If rolling update → likely transient, recommend monitoring
- If node pressure → escalate to node investigation
