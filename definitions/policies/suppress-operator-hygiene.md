---
name: suppress-operator-hygiene
kind: policy
version: 1.0.0
priority: 15
conditions:
  check_id_regex: "^(no-resource-limits|no-resource-requests|quota-.*|no-endpoints)$"
  is_operator_managed: true
action:
  type: suppress
  suppress_duration_minutes: 10080
---

Suppress hygiene checks (resource limits, quotas, endpoints) on OLM
operator-managed workloads. Operators control the pod spec — flagging
missing limits on operator-managed deployments is noise.

Override per-workload with annotation: `pinky.io/scan-override: "all"`
