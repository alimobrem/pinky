---
name: kubectl-rollout
kind: tool
version: 1.0.0
authz_class: observer_read
timeout_seconds: 10
parameters:
  - name: subcommand
    type: string
    required: true
    enum: [status, history]
  - name: resource_type
    type: string
    required: true
    enum: [deployment, statefulset, daemonset]
  - name: name
    type: string
    required: true
  - name: namespace
    type: string
    required: true
---
# kubectl rollout

Check rollout status and history for deployments, statefulsets, and daemonsets.

## Safety
- Read-only when using `status` and `history` subcommands
- Uses observer identity
- This tool does NOT support `undo` or `restart` — those are write operations
  handled by remediation tools

## Usage
- `status`: check if a rollout is progressing, complete, or stalled
- `history`: view revision history and change causes
- Useful for correlating deployment changes with observed failures
