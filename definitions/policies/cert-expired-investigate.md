---
name: cert-expired-investigate
kind: policy
version: 1.0.0
priority: 12
conditions:
  scanner: cert-expiry
  check_id: cert-expired
action:
  type: investigate
  risk_class: critical
  skill: investigate-cert-expiry
---
# Expired Certificate Investigation

Already-expired certificates are critical — services may be failing TLS
handshakes right now. Investigate immediately to determine blast radius
and whether cert-manager renewal is stuck or the issuer is misconfigured.
