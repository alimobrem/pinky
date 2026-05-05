---
name: daemonset-health
kind: scanner
version: 1.0.0
resource_kinds: [DaemonSet]
api_groups: [apps]
scan_interval_seconds: 120
timeout_seconds: 30
---
# DaemonSet Health Scanner

Checks for DaemonSets with missing or unavailable pods. Critical for
logging, monitoring, CNI, and storage components that must run on every node.

## Checks

### daemonset-unavailable
- severity: high
- condition: status.numberUnavailable > 0 for > 5 minutes
- evidence: DaemonSet status, unavailable nodes, pod events on affected nodes

### daemonset-misscheduled
- severity: medium
- condition: status.numberMisscheduled > 0
- evidence: DaemonSet node selector/tolerations, misscheduled node list

### daemonset-desired-mismatch
- severity: medium
- condition: status.desiredNumberScheduled != status.currentNumberScheduled
- evidence: DaemonSet status, node count, scheduling constraints
