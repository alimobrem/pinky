---
name: statefulset-investigate
kind: policy
version: 1.0.0
priority: 18
conditions:
  scanner: statefulset-health
action:
  type: investigate
  skill: investigate-statefulset
  risk_class: high
---
# StatefulSet Investigation

All statefulset-health scanner findings trigger investigation. StatefulSets
back databases, message queues, and other stateful workloads — issues here
have high blast radius.
