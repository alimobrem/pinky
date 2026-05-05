---
name: resource-quotas
kind: scanner
version: 1.0.0
resource_kinds: [ResourceQuota]
api_groups: [""]
scan_interval_seconds: 300
timeout_seconds: 30
checks:
  - id: quota-exceeded
    severity: high
    condition: {op: "quantity_gte", used_path: "used", hard_path: "hard"}
    resource_kind: ResourceQuota
    title_template: "ResourceQuota {namespace}/{name} exceeded"

  - id: quota-near-limit
    severity: medium
    condition: {op: "quantity_gte_pct", used_path: "used", hard_path: "hard", pct: 80}
    resource_kind: ResourceQuota
    title_template: "ResourceQuota {namespace}/{name} at >80% capacity"
---
# Resource Quota Scanner

Checks for namespaces approaching or exceeding resource quotas.
