---
name: investigate-generic
kind: skill
version: 1.0.0
description: Generic investigation for issues with no specific skill
tools: [kubectl-get, kubectl-describe, kubectl-events]
model_tier: reasoning
timeout_seconds: 120
---
# Generic Investigation

Fallback investigation skill for critical or unclassified observations.

1. Get the affected resource with `kubectl-describe` to see current state, conditions, and events
2. Get namespace events with `kubectl-events` to identify recent changes
3. Get related resources with `kubectl-get` (deployments, replicasets, services in the same namespace)

## Root cause framework

- Check for recent changes (new deployment, config change, scaling event)
- Check resource health (ready conditions, container states, restart counts)
- Check dependencies (referenced secrets, configmaps, services, PVCs)
- Check node conditions if the issue seems infrastructure-related

## Recommendation framework

- If caused by recent change → recommend rollback
- If resource misconfigured → recommend specific config fix
- If dependency missing → recommend creating the missing resource
- If unclear → summarize findings and recommend manual investigation with specific next steps
