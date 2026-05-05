---
name: daemonset-health
kind: scanner
version: 1.0.0
resource_kinds: [DaemonSet]
api_groups: [apps]
scan_interval_seconds: 120
timeout_seconds: 30
checks:
  - id: daemonset-unavailable
    severity: high
    condition: {path: "number_unavailable", op: "gt", value: 0}
    resource_kind: DaemonSet
    title_template: "DaemonSet {namespace}/{name} has unavailable pods"

  - id: daemonset-misscheduled
    severity: medium
    condition: {path: "number_misscheduled", op: "gt", value: 0}
    resource_kind: DaemonSet
    title_template: "DaemonSet {namespace}/{name} has misscheduled pods"

  - id: daemonset-desired-mismatch
    severity: medium
    condition:
      all:
        - {path: "desired_number_scheduled", op: "neq", value_from: "current_number_scheduled"}
    resource_kind: DaemonSet
    title_template: "DaemonSet {namespace}/{name} desired != current scheduled"
---
# DaemonSet Health Scanner

Checks for DaemonSets with unavailable, misscheduled, or missing pods.
