---
name: service-endpoints
kind: scanner
version: 1.0.0
resource_kinds: [Service]
api_groups: [""]
scan_interval_seconds: 120
timeout_seconds: 30
checks:
  - id: service-no-endpoints
    severity: high
    condition:
      all:
        - {path: "has_selector", op: "is_true"}
        - {path: "endpoints_ready", op: "eq", value: 0}
    resource_kind: Service
    title_template: "Service {namespace}/{name} has zero endpoints"

  - id: service-partial-endpoints
    severity: medium
    condition:
      all:
        - {path: "has_selector", op: "is_true"}
        - {path: "endpoints_ready", op: "gt", value: 0}
        - {path: "endpoints_not_ready_pct", op: "gt", value: 50}
    resource_kind: Service
    title_template: "Service {namespace}/{name} >50% endpoints not ready"
---
# Service Endpoint Health Scanner

Checks for services with no backing endpoints or degraded endpoint health.
