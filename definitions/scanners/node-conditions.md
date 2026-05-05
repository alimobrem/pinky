---
name: node-conditions
kind: scanner
version: 1.0.0
resource_kinds: [Node]
api_groups: [""]
scan_interval_seconds: 120
timeout_seconds: 30
checks:
  - id: memory-pressure
    severity: high
    condition: {path: "conditions", op: "condition_status", type: "MemoryPressure", status: "True"}
    resource_kind: Node
    title_template: "Node {name} MemoryPressure"

  - id: disk-pressure
    severity: high
    condition: {path: "conditions", op: "condition_status", type: "DiskPressure", status: "True"}
    resource_kind: Node
    title_template: "Node {name} DiskPressure"

  - id: pid-pressure
    severity: medium
    condition: {path: "conditions", op: "condition_status", type: "PIDPressure", status: "True"}
    resource_kind: Node
    title_template: "Node {name} PIDPressure"

  - id: not-ready
    severity: critical
    condition: {path: "conditions", op: "condition_status", type: "Ready", status: "False"}
    resource_kind: Node
    title_template: "Node {name} NotReady"

  - id: unschedulable
    severity: medium
    condition: {path: "unschedulable", op: "is_true"}
    resource_kind: Node
    title_template: "Node {name} cordoned (unschedulable)"
---
# Node Conditions Scanner

Checks for unhealthy node conditions: memory pressure, disk pressure,
PID pressure, NotReady, and cordoned nodes.
