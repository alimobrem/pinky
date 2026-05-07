---
name: pvc-capacity
kind: scanner
version: 1.0.0
resource_kinds: [PersistentVolumeClaim]
api_groups: [""]
scan_interval_seconds: 300
timeout_seconds: 30
checks:
  - id: pvc-nearly-full
    severity: high
    condition:
      op: promql_gt
      query: "kubelet_volume_stats_used_bytes{namespace=\"{namespace}\",persistentvolumeclaim=\"{name}\"} / kubelet_volume_stats_capacity_bytes{namespace=\"{namespace}\",persistentvolumeclaim=\"{name}\"}"
      value: 0.85
    title_template: "PVC {namespace}/{name} is over 85% full"
    payload_fields: [name, phase]
---
# PVC Capacity Scanner

Detects PersistentVolumeClaims that are over 85% full using Prometheus
kubelet volume stats. Requires Prometheus to be configured on the
cluster. PVCs approaching full capacity risk application failures when
writes are rejected.
