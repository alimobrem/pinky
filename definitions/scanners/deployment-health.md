---
name: deployment-health
kind: scanner
version: 1.0.0
resource_kinds: [Deployment]
api_groups: [apps]
scan_interval_seconds: 60
timeout_seconds: 30
checks:
  - id: rollout-stalled
    severity: high
    condition: {path: "conditions", op: "condition_status", type: "Progressing", status: "False"}
    resource_kind: Deployment
    title_template: "Deployment {namespace}/{name} rollout stalled"

  - id: replicas-unavailable
    severity: high
    condition: {path: "unavailable_replicas", op: "gte", value: 1}
    resource_kind: Deployment
    title_template: "Deployment {namespace}/{name} has unavailable replicas"

  - id: replica-mismatch
    severity: medium
    condition:
      all:
        - {path: "ready_replicas", op: "lt", value_from: "replicas"}
        - {path: "replicas", op: "gt", value: 0}
    resource_kind: Deployment
    title_template: "Deployment {namespace}/{name} ready replicas < desired"
---
# Deployment Health Scanner

Checks for stalled rollouts, unavailable replicas, and replica count mismatches.
