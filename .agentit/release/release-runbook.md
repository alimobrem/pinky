# Release Runbook: pinky

## Pre-Deployment Checklist

- [ ] All CI pipeline stages passed
- [ ] Security scan shows no Critical/High CVEs
- [ ] Compliance policies validated
- [ ] Staging deployment verified
- [ ] Database migrations applied (if applicable)
- [ ] Monitoring dashboards reviewed

## Canary Deployment Steps

| Step | Weight | Analysis Duration | Gate |
|------|--------|-------------------|------|
| 1 | 5% | 2 minutes | Automated (success rate >= 95%) |
| 2 | 25% | 2 minutes | Automated (success rate >= 95%) |
| 3 | 50% | 3 minutes | Automated (success rate >= 95%) |
| 4 | 100% | — | Full rollout |

**Auto-promotion:** Yes
**Criticality:** medium

## Monitoring During Rollout

```bash
# Watch rollout status
kubectl argo rollouts get rollout pinky --watch

# Check analysis runs
kubectl get analysisrun -l rollouts-pod-template-hash
```

## Rollback Procedures

```bash
# Abort current rollout (stops canary, routes all traffic to stable)
kubectl argo rollouts abort pinky

# Undo to previous revision
kubectl argo rollouts undo pinky

# Retry after fixing issues
kubectl argo rollouts retry rollout pinky
```

## Escalation

| Severity | Contact | Response Time |
|----------|---------|---------------|
| P1 — Full outage | On-call SRE | 15 minutes |
| P2 — Degraded | Team lead | 30 minutes |
| P3 — Minor | Ticket | Next business day |
