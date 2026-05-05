---
name: pod-health
kind: scanner
version: 1.0.0
resource_kinds: [Pod]
api_groups: ["", "apps"]
scan_interval_seconds: 60
timeout_seconds: 30
checks:
  - id: crash-loop-backoff
    severity: high
    iterate: containers[*]
    condition:
      all:
        - {path: "state.type", op: "eq", value: "waiting"}
        - {path: "state.reason", op: "eq", value: "CrashLoopBackOff"}
    resource_kind: Pod
    title_template: "Pod {namespace}/{name} in CrashLoopBackOff"
    payload_fields: [name, restart_count, state.reason]

  - id: oom-killed
    severity: critical
    iterate: containers[*]
    condition:
      all:
        - {path: "last_state.type", op: "eq", value: "terminated"}
        - {path: "last_state.reason", op: "eq", value: "OOMKilled"}
    resource_kind: Pod
    title_template: "Pod {namespace}/{name} OOMKilled"
    payload_fields: [name, last_state.exit_code]

  - id: excessive-restarts
    severity: medium
    iterate: containers[*]
    condition: {path: "restart_count", op: "gt", value: 5}
    resource_kind: Pod
    title_template: "Pod {namespace}/{name} excessive restarts"
    payload_fields: [name, restart_count]

  - id: image-pull-error
    severity: high
    iterate: containers[*]
    condition: {path: "state.reason", op: "in", value: ["ImagePullBackOff", "ErrImagePull"]}
    resource_kind: Pod
    title_template: "Pod {namespace}/{name} image pull error"
    payload_fields: [name, state.reason]

  - id: pending-too-long
    severity: medium
    condition:
      all:
        - {path: "phase", op: "eq", value: "Pending"}
        - {path: "creation_timestamp", op: "age_gt", value: "5m"}
    resource_kind: Pod
    title_template: "Pod {namespace}/{name} stuck Pending >5m"
---
# Pod Health Scanner

Checks for unhealthy pod states across the cluster: CrashLoopBackOff,
OOMKilled, excessive restarts, image pull errors, and pods stuck Pending.
