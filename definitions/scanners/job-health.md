---
name: job-health
kind: scanner
version: 1.0.0
resource_kinds: [Job, CronJob]
api_groups: [batch]
scan_interval_seconds: 120
timeout_seconds: 30
checks:
  - id: job-failed
    severity: high
    condition:
      all:
        - {path: "kind", op: "eq", value: "Job"}
        - {path: "failed", op: "gte", value_from: "backoff_limit"}
    resource_kind: Job
    title_template: "Job {namespace}/{name} failed (backoff limit reached)"

  - id: job-deadline-exceeded
    severity: high
    condition:
      all:
        - {path: "kind", op: "eq", value: "Job"}
        - {path: "conditions", op: "condition_status", type: "DeadlineExceeded", status: "True"}
    resource_kind: Job
    title_template: "Job {namespace}/{name} deadline exceeded"

  - id: cronjob-missed
    severity: medium
    condition:
      all:
        - {path: "kind", op: "eq", value: "CronJob"}
        - {path: "last_schedule_time", op: "age_gt", value: "2h"}
    resource_kind: CronJob
    title_template: "CronJob {namespace}/{name} missed schedule (>2h since last run)"
---
# Job / CronJob Health Scanner

Checks for failed Jobs (backoff limit reached, deadline exceeded) and
CronJobs that have missed their schedule.
