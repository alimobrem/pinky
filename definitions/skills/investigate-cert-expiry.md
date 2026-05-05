---
name: investigate-cert-expiry
kind: skill
version: 1.0.0
description: Investigate certificate expiration issues
tools: [kubectl-get, kubectl-describe, kubectl-events]
model_tier: utility
timeout_seconds: 60
---
# Investigate Certificate Expiry

When investigating expired or soon-to-expire certificates:

1. Get the Certificate resource with `kubectl-describe` to check status, conditions, and renewal state
2. Get events for the Certificate with `kubectl-events` to see issuance/renewal history
3. Check the Issuer/ClusterIssuer with `kubectl-get` to verify it's ready
4. Check the Secret containing the TLS cert with `kubectl-get` to verify it exists and has data

## Root cause categories

### cert-manager renewal failure
- Issuer not ready (ACME account issue, CA secret missing)
- Challenge solver failing (DNS or HTTP-01 challenge not completing)
- Rate limit hit on the ACME provider (Let's Encrypt)
- Certificate resource has invalid spec (wrong dnsNames, wrong issuerRef)

### Manual certificate
- No cert-manager — certificate was manually created and has no auto-renewal
- Operator forgot to rotate

### Infrastructure
- Ingress controller not picking up the renewed secret
- Secret exists but is in wrong namespace
- Multiple ingresses referencing different secrets for same domain

## Recommendation framework

- If cert-manager issuer not ready → recommend fixing issuer configuration
- If challenge failing → recommend checking DNS/HTTP-01 solver config
- If rate limited → recommend waiting or switching to staging issuer
- If manual cert → recommend installing cert-manager or manual rotation now
- If already expired → flag as urgent, recommend immediate manual rotation while fixing auto-renewal
