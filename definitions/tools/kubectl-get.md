---
name: kubectl-get
kind: tool
version: 1.0.0
authz_class: observer_read
timeout_seconds: 10
parameters:
  - name: resource_type
    type: string
    required: true
  - name: name
    type: string
    required: false
  - name: namespace
    type: string
    required: false
  - name: label_selector
    type: string
    required: false
---
# kubectl get

Retrieves Kubernetes resources from a cluster. Returns JSON output.

## Safety
- Read-only operation
- Uses observer identity for standard resources
- Requires user identity for: secrets, configmaps with sensitive annotations

## Usage
For list operations, returns items array. For single resource, returns the resource object.
Supports label selectors for filtering.
