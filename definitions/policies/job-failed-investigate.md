---
name: job-failed-investigate
kind: policy
version: 1.0.0
priority: 25
conditions:
  scanner: job-health
  severity_gte: high
action:
  type: investigate
  skill: investigate-job-failure
---
# Failed Job Investigation

High-severity job failures (backoff limit reached, deadline exceeded)
trigger investigation. Low-severity findings like suspended CronJobs
stay in Watch.
