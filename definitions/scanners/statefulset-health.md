---
name: statefulset-health
kind: scanner
version: 1.0.0
resource_kinds: [StatefulSet]
api_groups: [apps]
scan_interval_seconds: 60
timeout_seconds: 30
checks:
  - id: sts-rollout-stuck
    severity: high
    condition:
      all:
        - {path: "current_revision", op: "neq", value_from: "update_revision"}
        - {path: "updated_replicas", op: "lt", value_from: "replicas"}
    resource_kind: StatefulSet
    title_template: "StatefulSet {namespace}/{name} rollout stuck"

  - id: sts-replicas-unavailable
    severity: high
    condition: {path: "ready_replicas", op: "lt", value_from: "replicas"}
    resource_kind: StatefulSet
    title_template: "StatefulSet {namespace}/{name} has unavailable replicas"
---
# StatefulSet Health Scanner

Checks for stuck rollouts and unavailable replicas in StatefulSets.
