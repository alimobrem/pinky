---
name: cert-expiry
kind: scanner
version: 1.0.0
resource_kinds: [Secret]
api_groups: ["", "cert-manager.io"]
scan_interval_seconds: 3600
timeout_seconds: 30
checks:
  - id: cert-expired
    severity: critical
    condition: {path: "tls_crt", op: "cert_expired"}
    resource_kind: Secret
    title_template: "Certificate {namespace}/{name} has expired"

  - id: cert-expiring-soon
    severity: high
    condition: {path: "tls_crt", op: "cert_expires_within", value: "7d"}
    resource_kind: Secret
    title_template: "Certificate {namespace}/{name} expires within 7 days"
---
# Certificate Expiry Scanner

Checks TLS secrets for expired or soon-to-expire certificates.
Requires the tls.crt field in the secret data.
