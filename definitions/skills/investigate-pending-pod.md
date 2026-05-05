---
name: investigate-pending-pod
kind: skill
version: 1.0.0
description: Investigate pods stuck in Pending state
tools: [kubectl-get, kubectl-describe, kubectl-events, kubectl-top]
model_tier: utility
timeout_seconds: 60
---
# Investigate Pending Pods

When investigating pods stuck in Pending state (>5 minutes):

1. Get pod events with `kubectl-events` — scheduling failure reasons are here
2. Get pod description with `kubectl-describe` — check conditions and scheduling constraints
3. Get node resource usage with `kubectl-top` (resource_type: nodes) to check capacity
4. Get resource quotas with `kubectl-get` (resource_type: resourcequotas) in the namespace

## Root cause categories

### Insufficient resources
- No node has enough CPU or memory to schedule the pod
- Resource quota exceeded in the namespace
- LimitRange preventing the pod from being created

### Scheduling constraints
- NodeSelector or nodeAffinity doesn't match any node
- Taints and tolerations mismatch
- Pod anti-affinity preventing co-location
- TopologySpreadConstraints unsatisfiable

### Volume issues
- PersistentVolumeClaim pending (no matching PV or storage class)
- Volume already attached to another node (ReadWriteOnce)
- Storage class doesn't exist

## Recommendation framework

- If resource exhaustion → recommend scaling the node pool or adjusting requests
- If quota exceeded → recommend increasing quota or reducing other workloads
- If scheduling constraint → recommend relaxing constraints or adding matching nodes
- If PVC pending → recommend creating the PV or fixing the storage class
- If affinity conflict → recommend adjusting affinity rules
