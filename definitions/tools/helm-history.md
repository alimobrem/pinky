---
name: helm-history
kind: tool
version: 1.0.0
authz_class: observer_read
timeout_seconds: 10
parameters:
  - name: release_name
    type: string
    required: true
  - name: namespace
    type: string
    required: true
  - name: max_revisions
    type: integer
    required: false
    default: 10
---
# helm history

Returns the release history for a Helm chart, showing revisions, status,
and chart version changes.

## Safety
- Read-only operation
- Uses observer identity — release metadata is non-sensitive

## Usage
- Check whether a recent Helm upgrade coincides with the observed issue
- Identify failed or pending-rollback releases
- Compare chart versions across revisions to spot config drift
