# Remediation Flow

Complete lifecycle from issue detection to auto-completion.

## Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           OBSERVATION CYCLE                                │
│                                                                             │
│  Scanner ──▶ Observations ──▶ Correlator ──▶ Issue + Work Item (ready)     │
│                                    │                                        │
│                              Policy Engine                                  │
│                              ┌─────┴─────┐                                 │
│                         investigate   suppress                              │
│                              │                                              │
│                    _dispatch_investigation                                  │
│                    ┌─────────┴──────────┐                                   │
│                    │ Cooldown check     │                                    │
│                    │ (completed blocks) │                                    │
│                    └─────────┬──────────┘                                   │
│                              │ pass                                         │
│                              ▼                                              │
│                    InvestigationWorkflow                                     │
│                    (gather evidence → LLM → artifact)                       │
└─────────────────────────────────────────────────────────────────────────────┘

                              │ investigation complete
                              ▼

┌─────────────────────────────────────────────────────────────────────────────┐
│                        REMEDIATION LIFECYCLE                                │
│                                                                             │
│  ┌──────────┐     ┌───────────────────┐     ┌──────────────────────┐       │
│  │ User     │────▶│ POST /executions  │────▶│ Execution created    │       │
│  │ clicks   │     │ ?type=remediation │     │ status = pending     │       │
│  │ "Apply"  │     └───────────────────┘     └──────────┬───────────┘       │
│  └──────────┘                                          │                    │
│                                                        ▼                    │
│                               ┌────────────────────────────────────┐       │
│                               │  RemediationWorkflow (Temporal)    │       │
│                               │                                    │       │
│                               │  1. emit("started")                │       │
│                               │  2. validate_approval()            │       │
│                               │     ├── invalid ──▶ emit("failed") │       │
│                               │     │               reason:        │       │
│                               │     │               invalidated    │       │
│                               │     │                              │       │
│                               │  3. FOR each plan_step:            │       │
│                               │     ├── emit("progress")           │       │
│                               │     ├── apply_change()             │       │
│                               │     │   ├── decrypt binding token  │       │
│                               │     │   ├── K8s API call           │       │
│                               │     │   ├── emit("command")        │       │
│                               │     │   └── RAISE on failure ────┐ │       │
│                               │     │       (retried 2x)         │ │       │
│                               │     │                            │ │       │
│                               │  4. VerificationWorkflow         │ │       │
│                               │     ├── wait 60s                 │ │       │
│                               │     ├── check pod health         │ │       │
│                               │     └── return passed/failed     │ │       │
│                               │                                  │ │       │
│                               │  5. emit("completed")            │ │       │
│                               │     payload: {                   │ │       │
│                               │       verification_passed: bool  │ │       │
│                               │     }                            │ │       │
│                               │                            ┌─────┘ │       │
│                               │  CATCH CancelledError:     │       │       │
│                               │    emit("failed",          │       │       │
│                               │      reason: "cancelled")  │       │       │
│                               │                            │       │       │
│                               │  CATCH Exception:          │       │       │
│                               │    emit("failed",    ◀─────┘       │       │
│                               │      reason: "step_failed")       │       │
│                               └────────────────────────────────────┘       │
│                                          │                                  │
│                                          ▼                                  │
│                               ┌────────────────────────┐                   │
│                               │ project_to_postgres()  │                   │
│                               │                        │                   │
│                               │ IF completed:          │                   │
│                               │   execution → completed│                   │
│                               │   IF verification_     │                   │
│                               │   passed AND           │                   │
│                               │   remediation:         │                   │
│                               │   ┌─ TRANSACTION ────┐ │                   │
│                               │   │ task → done      │ │                   │
│                               │   │ issue → resolved │ │                   │
│                               │   │ pg_notify()      │ │                   │
│                               │   └──────────────────┘ │                   │
│                               │                        │                   │
│                               │ IF failed:             │                   │
│                               │   execution → failed   │                   │
│                               │   task stays open      │                   │
│                               └────────────────────────┘                   │
│                                          │                                  │
│                                          ▼                                  │
│                               ┌────────────────────────┐                   │
│                               │ SSE (pg_notify)        │                   │
│                               │ → pinky_watch           │                   │
│                               │ → pinky_execution_{id}  │                   │
│                               │ → pinky_work_items      │                   │
│                               └────────────────────────┘                   │
│                                          │                                  │
│                                          ▼                                  │
│                               ┌────────────────────────┐                   │
│                               │ Frontend               │                   │
│                               │ EventBus → invalidate  │                   │
│                               │ Terminal shows commands │                   │
│                               │ Toast on completion     │                   │
│                               │ Task moves to Done tab  │                   │
│                               └────────────────────────┘                   │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Failure Modes & Recovery

| Failure Point | What Happens | Recovery |
|--------------|--------------|----------|
| Temporal unavailable | API returns 503, execution marked failed | User retries |
| Approval expired | Workflow emits "failed: invalidated" | User re-investigates |
| K8s 403 on apply_change | Activity raises, retried 2x, then workflow fails | User fixes RBAC, retries |
| Binding token expired | Activity raises with clear message | User reconnects cluster |
| Token decryption fails | Activity raises | Check encryption key config |
| Verification fails | Task stays open, issue stays open | User reviews and decides |
| DB transaction fails | All or nothing — no partial done+open | System retries |
| SSE queue overflow | Event logged as warning, dropped | Client refetch on reconnect |
| Cancel mid-step | Steps already applied stay, workflow stops | User assesses partial state |

## Observability

- `GET /api/v1/health/workflows` — counts stuck/stale/orphaned/mismatched entities
- Worker logs: structured JSON with `execution_id`, `event_type`, `cluster_id`
- Temporal UI: workflow history, failed activities, retry counts
- Execution terminal: real-time `oc` commands visible to user
