---
name: kubectl-top
kind: tool
version: 1.0.0
authz_class: observer_read
timeout_seconds: 10
parameters:
  - name: resource_type
    type: string
    required: true
    enum: [pods, nodes]
  - name: namespace
    type: string
    required: false
  - name: name
    type: string
    required: false
  - name: sort_by
    type: string
    required: false
    enum: [cpu, memory]
---
# kubectl top

Returns current CPU and memory usage for pods or nodes. Requires metrics-server.

## Safety
- Read-only operation
- Uses observer identity — resource usage metrics are not sensitive

## Usage
- Use `resource_type: pods` with a namespace to check pod resource consumption
- Use `resource_type: nodes` to check node-level pressure
- Sort by memory when investigating OOM, sort by CPU when investigating throttling
- If metrics-server is unavailable, the tool returns an explicit error
