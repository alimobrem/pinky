---
name: service-endpoints
kind: scanner
version: 1.0.0
resource_kinds: [Service, Endpoints]
api_groups: [""]
scan_interval_seconds: 120
timeout_seconds: 30
---
# Service Endpoint Health Scanner

Checks for services with no backing endpoints. This is the #1 cause
of "the service is up but nobody can reach it" — a traffic blackhole.

## Checks

### service-no-endpoints
- severity: high
- condition: Service type ClusterIP/LoadBalancer/NodePort has 0 ready endpoints AND Service has a selector defined
- evidence: service selector, matching pods (or lack thereof), endpoint slices

### service-partial-endpoints
- severity: medium
- condition: Service has endpoints but > 50% of them are not ready
- evidence: endpoint count (ready vs not-ready), pod statuses for not-ready endpoints
