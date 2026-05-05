---
name: job-health
kind: scanner
version: 1.0.0
resource_kinds: [Job, CronJob]
api_groups: [batch]
scan_interval_seconds: 120
timeout_seconds: 30
---
# Job / CronJob Health Scanner

Checks for failed batch workloads. These are silent killers — batch
processing stops and nobody notices for hours.

## Checks

### job-failed
- severity: high
- condition: Job status.failed >= spec.backoffLimit (all retries exhausted)
- evidence: job status, pod logs from failed pods, events

### job-deadline-exceeded
- severity: high
- condition: Job condition DeadlineExceeded = True
- evidence: job spec.activeDeadlineSeconds vs actual duration, events

### cronjob-missed
- severity: medium
- condition: CronJob lastScheduleTime is > 2x the schedule interval ago
- evidence: CronJob schedule, lastScheduleTime, last successful time, active jobs

### cronjob-suspended
- severity: low
- condition: CronJob spec.suspend = true
- evidence: CronJob name, namespace, schedule, when it was last active
