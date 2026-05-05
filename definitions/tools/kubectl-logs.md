---
name: kubectl-logs
kind: tool
version: 1.0.0
authz_class: user_sensitive_read
timeout_seconds: 15
parameters:
  - name: pod_name
    type: string
    required: true
  - name: namespace
    type: string
    required: true
  - name: container
    type: string
    required: false
  - name: tail_lines
    type: integer
    required: false
    default: 100
  - name: previous
    type: boolean
    required: false
    default: false
---
# kubectl logs

Retrieves container logs from a pod. Returns the last N lines of stdout/stderr.

## Safety
- Read-only but classified as user_sensitive_read — logs may contain secrets,
  credentials, PII, or internal application state
- Requires the operator's own cluster identity, not the observer SA
- Output is passed through redaction rules before inclusion in evidence

## Usage
- Set `previous: true` to get logs from the previously terminated container
  (essential for CrashLoopBackOff and OOMKilled investigations)
- Default tail is 100 lines — sufficient for most crash diagnostics without
  overwhelming the evidence bundle
