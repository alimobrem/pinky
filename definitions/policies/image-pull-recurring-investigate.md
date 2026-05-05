---
name: image-pull-recurring-investigate
kind: policy
version: 1.0.0
priority: 30
conditions:
  scanner: pod-health
  check_id: image-pull-error
  recurrence_count_gte: 2
action:
  type: investigate
  skill: investigate-image-pull
---
# Image Pull Error Investigation

ImagePullBackOff that persists across 2+ scan cycles is likely a real
problem (wrong tag, registry auth, deleted image) rather than a transient
network blip. Investigate to determine root cause.
