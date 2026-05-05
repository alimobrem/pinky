---
name: prometheus-query
kind: tool
version: 1.0.0
authz_class: observer_read
timeout_seconds: 10
parameters:
  - name: query
    type: string
    required: true
    description: PromQL expression to execute
  - name: duration
    type: string
    required: false
    default: "5m"
    description: Time range for rate/increase functions
---
# Prometheus Query

Executes a PromQL query against the cluster's Thanos Querier (OpenShift
Cluster Monitoring Operator).

## Safety
- Read-only operation
- Uses observer identity -- metrics are non-sensitive
- Query timeout enforced at 10 seconds

## Usage
- Use for CPU throttling, memory usage trends, restart rates, error rates
- Queries are scoped to the cluster being investigated
- Results are scalar values or time series
- If Prometheus is unavailable, the tool returns an empty result (not an error)
