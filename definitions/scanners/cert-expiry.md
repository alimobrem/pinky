---
name: cert-expiry
kind: scanner
version: 1.0.0
resource_kinds: [Secret, Certificate]
api_groups: ["", "cert-manager.io"]
scan_interval_seconds: 3600
timeout_seconds: 30
---
# Certificate Expiry Scanner

Checks for certificates nearing expiration.

## Checks

### cert-expiring-soon
- severity: high
- condition: certificate notAfter within 7 days
- evidence: certificate subject, issuer, expiry date, namespace

### cert-expired
- severity: critical
- condition: certificate notAfter in the past
- evidence: certificate subject, issuer, expiry date, affected routes/ingresses
