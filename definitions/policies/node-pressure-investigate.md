---
name: node-pressure-investigate
kind: policy
version: 1.0.0
priority: 18
conditions:
  scanner: node-conditions
action:
  type: investigate
  skill: investigate-node-pressure
  risk_class: high
---
# Node Condition Investigation

All node-conditions scanner findings (MemoryPressure, DiskPressure,
PIDPressure, NotReady, Unschedulable) trigger investigation using the
node-pressure skill. Node-level issues affect all pods on the node.
