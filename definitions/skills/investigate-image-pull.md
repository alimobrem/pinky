---
name: investigate-image-pull
kind: skill
version: 1.0.0
description: Investigate ImagePullBackOff errors
tools: [kubectl-get, kubectl-describe, kubectl-events]
model_tier: utility
timeout_seconds: 60
---
# Investigate Image Pull Errors

When investigating ImagePullBackOff or ErrImagePull:

1. Get pod events with `kubectl-events` — the event message contains the registry error
2. Get pod description with `kubectl-describe` — check container image reference
3. Check if the image pull secret exists with `kubectl-get` (kind: Secret, namespace-scoped)

## Root cause categories

### Wrong image reference
- Typo in image name or tag
- Tag doesn't exist (e.g., `latest` removed, specific tag deleted)
- Registry hostname wrong

### Authentication failure
- Image pull secret missing or expired
- Secret references wrong registry
- Service account doesn't have the imagePullSecret attached

### Registry unavailable
- Registry is down or unreachable from the cluster
- Network policy blocking egress to registry
- Proxy configuration missing

## Recommendation framework

- If tag doesn't exist → recommend correcting the tag (show available tags if possible)
- If pull secret missing → recommend creating/attaching the secret
- If pull secret expired → recommend refreshing the credential
- If registry unreachable → flag as infrastructure issue, check network policies
