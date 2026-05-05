---
name: service-no-endpoints-investigate
kind: policy
version: 1.0.0
priority: 22
conditions:
  scanner: service-endpoints
  check_id: service-no-endpoints
action:
  type: investigate
  skill: investigate-service-endpoints
  risk_class: high
---
# Service Zero Endpoints Investigation

Services with zero endpoints are traffic blackholes — requests hit the
service IP and get connection refused. Investigate immediately.
