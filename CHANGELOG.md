# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.1.0] - 2026-05-18

### Added

- **Observation pipeline** — 13 markdown-driven scanners detect issues across pods, deployments, statefulsets, daemonsets, jobs, PVCs, services, resource quotas, HPAs, and resource usage
- **Policy engine** — 16 deterministic rules map scanner results to actions (suppress, observe, investigate, auto-resolve, create-task). Priority-ordered, first-match-wins. No LLM in the policy path
- **Investigation workflows** — Temporal-based workflows that gather evidence from clusters, redact credentials, and use LLM analysis to produce root cause + recommended action
- **Remediation with approval gate** — Signal-based approval on Temporal workflows with changeset digest validation, 4-hour timeout countdown, dry-run preview, and binding revalidation
- **Verification with retry** — Post-remediation verification checks target resources up to 3 times with 60s backoff
- **Auto-complete** — Verified remediations automatically complete the task and resolve the issue
- **Execution state machine** — 7 states (pending, running, waiting_for_approval, completed, failed, cancelled, timed_out) with validated transitions
- **Identity isolation** — Observer service account for reads, user OAuth token for writes. Never mixed
- **Credential encryption** — AES-256-GCM envelope encryption with key versioning and AAD binding
- **Evidence redaction** — 11 patterns redact secrets before LLM prompts
- **Multi-cluster support** — Per-cluster bindings with OAuth token refresh, expiry tracking, and revalidation
- **Web UI** — Dashboard, Tasks (with investigation results, approval gate, execution log), Watch (live observations), History (audit trail), Clusters, Settings
- **Brain chat** — Conversational interface with live cluster queries (tool use) and auto-generated charts
- **SSE real-time** — Singleton EventSource per session, pg_notify fan-out, heartbeat, reconnect
- **Markdown extensibility** — 53 definitions ship out of box (13 scanners, 8 tools, 11 skills, 16 policies, 3 pipelines, 2 redaction rules). Add new ones without code changes
- **CLI** — `pinky` command-line tool wrapping the REST API
- **Helm chart** — Production-ready Kubernetes/OpenShift deployment with non-root containers, read-only rootfs, NetworkPolicy support
- **1,156 tests** — 417 API + 611 worker unit + 70 worker integration + 36 evals + 22 contracts
