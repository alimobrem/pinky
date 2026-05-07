---
name: hpa-capacity
kind: scanner
version: 1.0.0
resource_kinds: [HorizontalPodAutoscaler]
api_groups: ["autoscaling"]
scan_interval_seconds: 120
timeout_seconds: 30
checks:
  - id: hpa-at-max
    severity: high
    condition:
      all:
        - {path: "current_replicas", op: "gte", value_from: "max_replicas"}
        - {path: "desired_replicas", op: "gt", value_from: "max_replicas"}
    title_template: "HPA {namespace}/{name} at max replicas, wants more"
    payload_fields: [current_replicas, max_replicas, desired_replicas]
---
# HPA Capacity Scanner

Detects Horizontal Pod Autoscalers that have scaled to their maximum
replica count and still want more. This indicates a capacity problem
where the workload needs more resources than the HPA is allowed to
provision.
