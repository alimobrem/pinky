---
name: suppress-completed-jobs
kind: policy
version: 1.0.0
priority: 15
conditions:
  scanner: job-health
  resource_namespace_regex: "^(openshift-|kube-)"
action:
  type: suppress
  suppress_duration_minutes: 10080
---
# Suppress System Namespace Job Noise

Suppresses job health observations from system namespaces for 7 days.
System jobs (image pruners, garbage collectors) are operator-managed
and not actionable by users.
