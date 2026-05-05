---
name: cert-expiring-observe
kind: policy
version: 1.0.0
priority: 50
conditions:
  scanner: cert-expiry
  check_id: cert-expiring-soon
action:
  type: observe
---
# Expiring Certificate Observation

Certificates expiring within 7 days are placed in Watch. Most clusters
have cert-manager auto-renewal — if the cert is still expiring after 2+
observations, the high-recurring-investigate policy will escalate it.
