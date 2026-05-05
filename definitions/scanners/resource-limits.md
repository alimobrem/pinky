---
name: resource-limits
kind: scanner
version: 1.0.0
resource_kinds: [Pod]
api_groups: [""]
scan_interval_seconds: 300
timeout_seconds: 30
checks:
  - id: no-resource-limits
    severity: medium
    iterate: containers[*]
    condition: {path: "resources.limits", op: "is_empty"}
    resource_kind: Pod
    title_template: "Pod {namespace}/{name} has no resource limits"
    payload_fields: [name]

  - id: no-resource-requests
    severity: low
    iterate: containers[*]
    condition: {path: "resources.requests", op: "is_empty"}
    resource_kind: Pod
    title_template: "Pod {namespace}/{name} has no resource requests"
    payload_fields: [name]
---
# Resource Limits Scanner

Detects pods running without resource limits or requests. Pods without
limits can consume unbounded resources and cause node pressure. Pods
without requests get BestEffort QoS and are first to be evicted.
