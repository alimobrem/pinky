---
name: ingress-health
kind: scanner
version: 1.0.0
resource_kinds: [Ingress]
api_groups: [networking.k8s.io, route.openshift.io]
scan_interval_seconds: 300
timeout_seconds: 30
checks:
  - id: ingress-no-backend
    severity: high
    condition: {path: "endpoints_ready", op: "eq", value: 0}
    resource_kind: Ingress
    title_template: "Ingress {namespace}/{name} has no healthy backends"
---
# Ingress/Route Health Scanner

Checks for ingress resources with no healthy backend endpoints.
