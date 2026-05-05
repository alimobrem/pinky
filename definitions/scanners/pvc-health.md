---
name: pvc-health
kind: scanner
version: 1.0.0
resource_kinds: [PersistentVolumeClaim]
api_groups: [""]
scan_interval_seconds: 300
timeout_seconds: 30
checks:
  - id: pvc-pending
    severity: high
    condition: {path: "phase", op: "eq", value: "Pending"}
    resource_kind: PersistentVolumeClaim
    title_template: "PVC {namespace}/{name} stuck Pending"

  - id: pvc-lost
    severity: critical
    condition: {path: "phase", op: "eq", value: "Lost"}
    resource_kind: PersistentVolumeClaim
    title_template: "PVC {namespace}/{name} Lost"
---
# PVC Health Scanner

Checks for PersistentVolumeClaims stuck in Pending or Lost state.
