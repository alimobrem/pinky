---
name: default-observe
kind: policy
version: 1.0.0
priority: 1000
conditions: {}
action:
  type: observe
---
# Default Observe Policy

Catch-all policy — any observation that doesn't match a more specific rule
is placed in Watch for monitoring. This is the lowest-priority rule.
