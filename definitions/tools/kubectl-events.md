---
name: kubectl-events
kind: tool
version: 1.0.0
authz_class: observer_read
timeout_seconds: 10
parameters:
  - name: namespace
    type: string
    required: false
  - name: field_selector
    type: string
    required: false
  - name: resource_name
    type: string
    required: false
  - name: resource_kind
    type: string
    required: false
---
# kubectl events

Retrieves Kubernetes events, optionally filtered by namespace and involved object.

## Safety
- Read-only operation
- Uses observer identity — events are non-sensitive cluster metadata

## Usage
- Filter by `resource_name` and `resource_kind` to get events for a specific
  resource (e.g., a failing pod or deployment)
- Use `field_selector` for advanced filtering (e.g., `type=Warning`)
- Events are sorted by last timestamp, most recent first
- Useful for understanding scheduling failures, image pull errors, and
  node-level issues without needing pod logs
