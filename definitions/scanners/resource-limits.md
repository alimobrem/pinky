---
name: resource-limits
kind: scanner
version: 2.0.0
resource_kinds: [Deployment, StatefulSet, DaemonSet, Job, CronJob]
api_groups: ["apps", "batch"]
scan_interval_seconds: 300
timeout_seconds: 30
checks:
  - id: no-resource-limits
    severity: medium
    iterate: containers[*]
    condition: {path: "resources.limits", op: "is_empty"}
    title_template: "{namespace}/{name} has containers without resource limits"
    payload_fields: [name]

  - id: no-resource-requests
    severity: low
    iterate: containers[*]
    condition: {path: "resources.requests", op: "is_empty"}
    title_template: "{namespace}/{name} has containers without resource requests"
    payload_fields: [name]
---
# Resource Limits Scanner

Detects workloads running without resource limits or requests. Scans
Deployments, StatefulSets, DaemonSets, Jobs, and CronJobs — the
controller resources where limits are actually configured. Workloads
without limits can consume unbounded resources and cause node pressure.
Workloads without requests get BestEffort QoS and are first to be evicted.
