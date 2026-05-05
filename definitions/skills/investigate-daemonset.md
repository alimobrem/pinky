---
name: investigate-daemonset
kind: skill
version: 1.0.0
description: Investigate DaemonSet availability and scheduling issues
tools: [kubectl-get, kubectl-describe, kubectl-events, kubectl-top]
model_tier: utility
timeout_seconds: 60
---
# Investigate DaemonSet Issues

DaemonSets must run on every eligible node. Gaps mean logging, monitoring,
or CNI is missing from some nodes.

1. Get DaemonSet description with `kubectl-describe` — check node selector, tolerations, update strategy
2. Get node list with `kubectl-get` — which nodes are missing the DaemonSet pod?
3. Get events for the DaemonSet with `kubectl-events` — scheduling failures
4. Check node resource usage with `kubectl-top` — is there capacity for the pod?

## Root cause categories

### Pods unavailable
- Node doesn't have enough resources (CPU/memory) for the DaemonSet pod
- Node has a taint the DaemonSet doesn't tolerate
- DaemonSet pod is crashing on specific nodes (node-specific issue)
- Image pull failure on specific nodes (registry access varies by node)

### Misscheduled
- DaemonSet running on nodes it shouldn't (node selector too broad)
- Node labels changed after DaemonSet was created

### Desired mismatch
- New nodes added but DaemonSet hasn't scheduled yet (transient)
- Nodes cordoned/draining

## Recommendation framework

- If resource exhaustion → recommend reducing DaemonSet resource requests or scaling nodes
- If taint mismatch → recommend adding toleration to DaemonSet
- If node-specific crash → recommend investigating the specific node
- If misscheduled → recommend tightening node selector
