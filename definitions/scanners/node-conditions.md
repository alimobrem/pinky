---
name: node-conditions
kind: scanner
version: 1.0.0
resource_kinds: [Node]
api_groups: [""]
scan_interval_seconds: 120
timeout_seconds: 30
---
# Node Conditions Scanner

Checks for unhealthy node conditions across the cluster.

## Checks

### memory-pressure
- severity: high
- condition: status.conditions where type == "MemoryPressure" and status == "True"
- evidence: node conditions, allocatable vs capacity, top pod consumers

### disk-pressure
- severity: high
- condition: status.conditions where type == "DiskPressure" and status == "True"
- evidence: node conditions, ephemeral storage usage

### pid-pressure
- severity: medium
- condition: status.conditions where type == "PIDPressure" and status == "True"
- evidence: node conditions, pod count on node

### not-ready
- severity: critical
- condition: status.conditions where type == "Ready" and status != "True"
- evidence: node conditions, recent events, kubelet status

### unschedulable
- severity: medium
- condition: spec.unschedulable == true (cordoned)
- evidence: node taints, cordon reason (if annotated)
