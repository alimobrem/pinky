---
name: investigate-node-pressure
kind: skill
version: 1.0.0
description: Investigate node resource pressure and evictions
tools: [kubectl-get, kubectl-describe, kubectl-top, kubectl-events]
model_tier: reasoning
timeout_seconds: 120
---
# Investigate Node Pressure

When investigating node resource pressure (MemoryPressure, DiskPressure, PIDPressure):

1. Get node description with `kubectl-describe` to check conditions, taints, and allocatable resources
2. Get node resource usage with `kubectl-top` (resource_type: nodes) to see current utilization
3. Get pod resource usage on the node with `kubectl-top` (resource_type: pods) to find top consumers
4. Get node events with `kubectl-events` to see eviction history and pressure transitions

## Root cause categories

### Memory pressure
- One or more pods consuming more memory than expected
- Memory leak in a workload (RSS growing over time)
- Too many pods scheduled on the node (overcommit)
- Node has less allocatable memory than expected (system reserved too low)

### Disk pressure
- Container logs consuming disk (no log rotation)
- Container images filling ephemeral storage
- Emptydir volumes growing unbounded
- PVs on the node filling up

### PID pressure
- Workload spawning too many processes
- Fork bomb or runaway process creation
- Too many containers on the node

## Recommendation framework

- If single pod is the top consumer → recommend resource limits or vertical scaling
- If overcommitted → recommend adding nodes or reducing pod count
- If memory leak suspected → recommend profiling and short-term restart
- If disk pressure → recommend log rotation, image pruning, or storage expansion
- If widespread → recommend cluster autoscaler review
