---
name: resource-limits-investigate
kind: policy
version: 1.0.0
priority: 50
conditions:
  check_id_regex: "^no-resource-limits$"
  severity_gte: medium
  recurrence_count_gte: 3
action:
  type: investigate
  skill: investigate-resource-limits
---
# Investigate Missing Resource Limits

Missing resource limits (medium severity) that recur 3+ scan cycles
get a targeted investigation using Prometheus metrics to derive
right-sized resource requests and limits based on actual usage.
