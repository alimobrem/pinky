---
name: pod-resource-usage
kind: scanner
version: 1.0.0
resource_kinds: [Pod]
api_groups: [""]
scan_interval_seconds: 300
timeout_seconds: 30
checks:
  - id: cpu-throttled
    severity: medium
    condition:
      op: promql_gt
      query: "rate(container_cpu_cfs_throttled_seconds_total{namespace='{namespace}',pod='{name}'}[5m])"
      value: 0.5
    resource_kind: Pod
    title_template: "Pod {namespace}/{name} CPU heavily throttled"
  - id: memory-near-limit
    severity: high
    condition:
      op: promql_gt
      query: "container_memory_working_set_bytes{namespace='{namespace}',pod='{name}'} / on() container_spec_memory_limit_bytes{namespace='{namespace}',pod='{name}'}"
      value: 0.9
    resource_kind: Pod
    title_template: "Pod {namespace}/{name} memory at >90% of limit"
  - id: high-restart-rate
    severity: high
    condition:
      op: promql_gt
      query: "rate(kube_pod_container_status_restarts_total{namespace='{namespace}',pod='{name}'}[1h])"
      value: 3
    resource_kind: Pod
    title_template: "Pod {namespace}/{name} restarting >3x per hour"
---
# Pod Resource Usage Scanner

Detects resource pressure using Prometheus metrics from the cluster's
Monitoring Operator. Requires Thanos Querier to be accessible.

## Checks

### cpu-throttled
Detects pods where CPU CFS throttling rate exceeds 50% over 5 minutes.
Indicates the pod needs higher CPU limits or the workload needs optimization.

### memory-near-limit
Detects pods using >90% of their memory limit. These are at risk of OOMKill.

### high-restart-rate
Detects pods restarting more than 3 times per hour, indicating instability.
