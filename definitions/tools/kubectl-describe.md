---
name: kubectl-describe
kind: tool
version: 1.0.0
authz_class: observer_read
timeout_seconds: 15
parameters:
  - name: resource_type
    type: string
    required: true
  - name: name
    type: string
    required: true
  - name: namespace
    type: string
    required: false
---
# kubectl describe

Returns detailed description of a Kubernetes resource including events, conditions, and status.

## Safety
- Read-only operation
- Uses observer identity
