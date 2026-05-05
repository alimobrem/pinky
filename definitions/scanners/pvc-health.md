---
name: pvc-health
kind: scanner
version: 1.0.0
resource_kinds: [PersistentVolumeClaim, PersistentVolume]
api_groups: [""]
scan_interval_seconds: 300
timeout_seconds: 30
---
# PVC Health Scanner

Checks for volume-related issues.

## Checks

### pvc-pending
- severity: high
- condition: PVC phase == "Pending" for > 5 minutes
- evidence: PVC events, storage class, requested capacity

### pvc-lost
- severity: critical
- condition: PVC phase == "Lost"
- evidence: PVC events, bound PV status, affected pods

### pv-released
- severity: medium
- condition: PV phase == "Released" (not reclaimed)
- evidence: PV reclaim policy, associated PVC, storage class
