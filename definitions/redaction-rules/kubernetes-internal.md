---
name: kubernetes-internal
kind: redaction-rule
version: 1.0.0
priority: 2
---
# Kubernetes Internal Redaction

Patterns to redact from evidence that contain Kubernetes internal credentials
and service account tokens.

## Service account tokens
- Paths matching `/var/run/secrets/kubernetes.io/serviceaccount/token` → [REDACTED-SA-TOKEN]
- JWT tokens starting with `eyJ` that contain `kubernetes.io` in decoded payload → [REDACTED-K8S-JWT]

## Kubeconfig fragments
- `certificate-authority-data:` values → [REDACTED-CA-DATA]
- `client-certificate-data:` values → [REDACTED-CLIENT-CERT]
- `client-key-data:` values → [REDACTED-CLIENT-KEY]
- `token:` values in kubeconfig user blocks → [REDACTED-TOKEN]

## Helm secrets
- Helm release secrets (`sh.helm.release.v1.*`) data field → [REDACTED-HELM-RELEASE]

## Cloud provider metadata
- AWS metadata tokens: `X-aws-ec2-metadata-token: .*` → [REDACTED-AWS-METADATA]
- GCP metadata: `Metadata-Flavor: Google` response bodies containing access tokens → [REDACTED-GCP-TOKEN]

## Behavior
- These rules supplement builtin-secrets, not replace them
- Redaction failures fail closed
