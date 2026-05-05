---
name: investigate-job-failure
kind: skill
version: 1.0.0
description: Investigate failed Jobs and missed CronJobs
tools: [kubectl-get, kubectl-describe, kubectl-events, kubectl-logs]
model_tier: utility
timeout_seconds: 60
---
# Investigate Job / CronJob Failures

1. Get job description with `kubectl-describe` — check conditions, completions, parallelism
2. Get events for the job with `kubectl-events` — scheduling, image pull, or runtime errors
3. Get logs from failed pods with `kubectl-logs` (previous=true) — the exit reason is here
4. For CronJobs: check schedule, lastScheduleTime, and whether the job is suspended

## Root cause categories

### Job failed (backoff limit reached)
- Application error (check pod logs for stack trace)
- Missing config/secret (check events for mount failures)
- Resource limits too low (OOM during batch processing)
- Deadline exceeded (job takes longer than activeDeadlineSeconds)

### CronJob missed schedule
- CronJob suspended (spec.suspend=true)
- Previous job still running (concurrencyPolicy=Forbid)
- Scheduler overloaded (>100 missed start times = auto-suspend)
- CronJob controller not running

## Recommendation framework

- If application error → recommend fixing the image/config and re-triggering
- If resource limits → recommend increasing limits for batch workloads
- If deadline exceeded → recommend increasing deadline or optimizing job
- If CronJob suspended → check if intentional, recommend unsuspending
- If concurrency conflict → recommend switching to Replace policy or increasing parallelism
