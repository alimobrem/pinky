---
name: resource-quotas
kind: scanner
version: 1.0.0
resource_kinds: [ResourceQuota, LimitRange]
api_groups: [""]
scan_interval_seconds: 300
timeout_seconds: 30
---
# Resource Quota Scanner

Checks for namespaces approaching or exceeding resource quotas.

## Checks

### quota-exceeded
- severity: high
- condition: ResourceQuota status.used >= status.hard for any resource
- evidence: quota name, namespace, resource type, used vs hard limits

### quota-near-limit
- severity: medium
- condition: ResourceQuota status.used >= 80% of status.hard for any resource
- evidence: quota name, namespace, resource type, used vs hard limits, percentage
