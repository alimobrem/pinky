---
name: ingress-health
kind: scanner
version: 1.0.0
resource_kinds: [Ingress, Route]
api_groups: [networking.k8s.io, route.openshift.io]
scan_interval_seconds: 300
timeout_seconds: 30
---
# Ingress/Route Health Scanner

Checks for issues with ingress and OpenShift route resources.

## Checks

### ingress-no-backend
- severity: high
- condition: Ingress rule references a service that doesn't exist or has no endpoints
- evidence: ingress name, namespace, missing service, host rules

### route-rejected
- severity: high
- condition: Route status.ingress[].conditions contains Admitted=False
- evidence: route name, namespace, rejection reason, router name

### tls-termination-missing
- severity: medium
- condition: Ingress/Route serves HTTPS host but has no TLS secret configured
- evidence: ingress name, namespace, host, expected TLS secret
