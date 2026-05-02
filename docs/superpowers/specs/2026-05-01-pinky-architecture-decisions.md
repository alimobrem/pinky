# Pinky Resolved Architecture Decisions

## Purpose

This document records the architecture and product decisions that have been explicitly chosen for `Pinky`. These decisions should be treated as binding constraints for the PRD, SDS, UI design, and implementation plans unless a later design review intentionally replaces them.

## Branding

- Product/platform name: `Pinky`
- Embedded SRE agent name: `The Brain`

## Product Shape

- `Pinky` is a greenfield product, not a compatibility-first rewrite of `pulse-agent`
- `Pinky` bundles its own UI, API, worker/runtime, shared contracts, and design system
- Core product surfaces:
  - `Tasks`
  - `Watch`
  - `History`
  - `Alerts`

## Tenancy And Workspace

- `Pinky` uses a single shared workspace model
- It is not designed as a multi-tenant SaaS platform
- It is not designed as multiple internal workspaces/teams with separate tenancy boundaries

## Cluster Registry And Access

- Clusters are added to a shared registry by Pinky admins/platform operators
- End users do not directly create shared clusters
- Users create per-cluster bindings on top of the shared registry
- V1 cluster registration method should integrate with an existing fleet manager such as ACM/OCM
- V1 user binding methods should support:
  - per-cluster OAuth/login where available (deployments with ≤5 clusters only)
  - brokered/admin-managed binding
  - not manual token or kubeconfig entry by default
- **For deployments with more than 5 clusters, external OIDC (via OpenShift's external OIDC feature) is required.** Per-cluster OAuth does not scale beyond 5 clusters. One external OIDC provider trusted by all managed clusters provides a single login across the fleet.
- If a cluster is removed from the registry:
  - active tasks/executions tied to it should be archived or closed
  - historical records remain available in read-only form for audit
- Live `Tasks`, `Watch`, and detailed issue data should only be visible for clusters the user currently has a valid binding for
- Historical records remain visible even if the user later loses cluster binding access

## Authentication

- Product login supports:
  - OpenShift OAuth
  - optional external OIDC
- One Pinky principal may link multiple identity providers to the same account
- Identity providers should auto-link to the same Pinky principal when the email is verified and matches
- Product authentication is server-managed
- Browser clients should use secure HTTP-only session cookies, not browser-held bearer tokens

## Session Management

- Product sessions are server-side and revocable
- Sessions must support:
  - idle timeout
  - absolute timeout
  - rotation after login or privilege elevation
  - logout
  - revocation
  - CSRF protection
- Cluster bindings should use a hybrid freshness model:
  - long-lived and refreshable for normal use
  - fresh reauth required for stale or sensitive actions
- If a product session or cluster binding expires while an execution is already running, the in-flight execution may continue if already authorized, but new user actions must be blocked until reauthentication

## Cluster Identity Model

Two separate cluster-side identities must exist:

### 1. Observer identity

- A read-only service account per cluster may be used for:
  - continuous background observation
  - standard non-sensitive reads

### 2. User execution identity

- The user's own cluster identity is required for:
  - any mutation or write action
  - any high-sensitivity read

### Sensitive reads

Sensitive reads should not use the read-only observer service account. They require the user's own identity. This includes categories such as:

- secrets
- terminal / exec-like access
- kubeconfig-like material
- private application data
- any similarly sensitive operational surface

### Standard reads

Non-sensitive standard reads may use the observer identity, including:

- background observation and scanner reads
- task/watch list summaries
- standard issue and task metadata
- non-sensitive topology and impact summaries

## Authorization Model

Authorization must be evaluated in three layers:

1. Product authorization
2. Cluster authorization
3. Execution authorization

Execution authorization should distinguish at least:

- product-authenticated read
- observer read
- user-sensitive read
- user write
- admin-only control-plane action

The top-level cluster selector should use a hybrid semantic model:

- overview surfaces may show multi-cluster summaries
- detailed task/workspace/execution surfaces are cluster-scoped

## Observation Model

- Pinky may continuously observe registered clusters using read-only observer identities
- Pinky does not require an active user session to maintain basic background observation
- User identity is still required for action execution and sensitive reads

## Source Of Truth

The source-of-truth model is hybrid:

- **Temporal** is authoritative for in-flight workflow and execution progress
- **Postgres** is authoritative for:
  - issues
  - tasks / work items
  - history
  - read models / projections

This implies Pinky needs an explicit projection model between workflow execution and durable queryable state.

## Approval Model

- The assignee may approve their own risky actions
- Approval applies to an exact, immutable change-set or execution payload
- If the issue, target resources, or change-set changes before execution:
  - approval is invalidated
  - a new approval is required
- Fresh reauthentication should be policy-based:
  - very high-risk actions always require fresh reauth
  - lower-risk actions require fresh reauth only when the session or binding is stale

## Task Model

- `Tasks` contains only human-actionable work with a plan
- Raw signals do not appear directly as task rows
- Low-confidence issues stay in `Watch`
- Tasks are team-visible but person-ownable
- The task lifecycle is human-centered:
  - `ready`
  - `accepted`
  - `in_progress`
  - `blocked`
  - `waiting_for_approval`
  - `done`
- Completed work should live in `History` as the canonical surface; `Tasks` may show at most transient completion feedback, not a persistent long-lived done queue
- If a user loses binding access to a cluster, any assigned tasks for that cluster should return to the team queue instead of remaining assigned but unusable

## UI Model

- `Watch` is separate from `Tasks`
- `History` is separate from both current work and raw signals
- `Alerts` remains a raw signal surface
- The Brain should be ambient and visible in the product, not hidden behind a chat-only interaction model

## Topology And Investigation

- Topology should be question-driven and perspective-based
- Pinky should support impact / blast-radius style investigation views
- Task/work-item detail should use hydrated workspaces backed by stored investigation/plan artifacts with bounded live refresh

## Security Baseline

- Strict CSP from day one
- No raw provider or cluster tokens in browser storage
- No raw provider or cluster tokens in prompts
- Token forwarding rules must be explicit and auditable
- Observer credentials and user execution credentials must be isolated
- Session and cluster-binding material must be encrypted at rest

## Resilience And Timeouts

The platform must define explicit timeout and retry classes for:

- product sessions
- cluster binding freshness
- SSE/streaming
- LLM calls
- workflow execution
- approval expiry
- verification delay
- integration timeouts

## Scale Targets

Initial serious production target:

- 10–100 clusters
- dozens to low hundreds of users
- task freshness target: under 10 seconds
- watch/execution update latency target: under 10 seconds

## Retention

- Keep history/audit/execution records online for 90 days as the default
- Archive or export older records after that primary online window
- Policy-configurable retention per record type is deferred to v2

---

## ADR-01: PostgreSQL Rationale

**Status:** Accepted

**Context:** Pinky needs a durable, ACID-compliant store for projections, issues, work items, history events, and execution events.

**Decision:**
- PostgreSQL for ACID projections, work items, issues, and history
- JSON/JSONB column support for flexible event payloads and investigation artifacts without requiring schema migration for every payload shape change
- pg_partman for time-based partitioning of history and execution event tables
- Mature ecosystem: proven tooling, monitoring, backup, and replication support

**Alternatives rejected:**
- TimescaleDB: overkill for v1 scale (10-100 clusters)
- Separate OLAP store: deferred; only justified if query patterns later demand analytical workloads that degrade OLTP performance

---

## ADR-02: Database Migration Strategy

**Status:** Accepted

**Decision:**
- Alembic for all schema migrations
- All migrations must be reversible (both upgrade and downgrade paths required)
- Blue-green compatible: no breaking schema changes without a dedicated migration window
- Migration sequence: new migrations run **before** new code deploys. New code must be backward-compatible with both the old and new schema during rollout.
- Every migration must be tested in CI against a real PostgreSQL instance
- No `DROP COLUMN` or `DROP TABLE` without a two-phase migration (add new -> migrate data -> drop old in a subsequent release)

---

## ADR-03: Secret Encryption Approach

**Status:** Accepted

**Decision:**
- AES-256-GCM envelope encryption for all sensitive fields
- Application-level field encryption for cluster tokens, observer bindings, and session material — not relying solely on database-level TDE
- Key wrapping:
  - **Production:** KMS (AWS KMS, Vault, or equivalent) wraps the data encryption key (DEK)
  - **Development:** environment-variable-provided master key wraps the DEK
- 90-day mandatory key rotation for DEKs
- Re-encryption of existing ciphertext on key rotation (batch background job)
- Encrypted fields are stored as opaque blobs; the application decrypts only when needed and never logs plaintext
- Decryption failures must fail closed (deny access, not fall back to plaintext)

---

## ADR-04: Temporal Namespace Strategy

**Status:** Accepted

**Decision:**
- Single Temporal namespace: `pinky`
- Task queues per workflow type:
  - `investigation` — issue investigation workflows
  - `remediation` — remediation and rollback workflows
  - `observation` — cluster observer polling loops
  - `projection` — event projection and materialization workflows
- Worker pools per task queue, independently scalable
- Workflow versioning uses Temporal's built-in versioning mechanism (workflow.get_version / patching), not namespace-per-version

**Rationale:**
- Single namespace simplifies operational overhead for v1 scale
- Per-type task queues allow independent scaling (observation workers scale with cluster count, investigation workers scale with issue volume)

---

## ADR-05: SSE vs WebSocket

**Status:** Accepted

**Decision:** SSE (Server-Sent Events) for all real-time server-to-client streams.

**Rationale:**
- Unidirectional server-to-client fits the read-heavy projection model
- Simpler infrastructure: no sticky sessions or WebSocket-aware load balancers required
- Native browser `EventSource` reconnect with `Last-Event-ID` provides built-in resume semantics
- SSE heartbeats are explicit and distinct from domain events

**WebSocket is only reconsidered if:**
- A concrete bidirectional real-time need emerges (e.g., interactive terminal sessions)
- SSE connection limits become a bottleneck beyond v1 targets

---

## ADR-06: Session Store Implementation

**Status:** Accepted

**Decision:**
- **Redis** for the active session store: fast TTL-based expiry, atomic operations for rotation/revocation, Redis cluster mode for HA
- **PostgreSQL** for the session audit log: append-only log of session creation, rotation, revocation, and expiry events
- Session data encrypted at rest using the same AES-256-GCM envelope encryption as cluster bindings (ADR-03)
- Redis is treated as ephemeral: session loss = user must re-login. No critical state depends solely on Redis without a PostgreSQL backing record.

---

## ADR-07: API Versioning Strategy

**Status:** Accepted

**Decision:**
- URL-based versioning: `/v1/clusters`, `/v1/work-items`, etc.
- Backward-compatible changes within a version (additive fields, new optional query parameters)
- Breaking changes require a new version (`/v2/...`)
- 6-month deprecation window for old versions after a new version is released
- Deprecation communicated via `Sunset` and `Deprecation` HTTP headers
- Contract tests in CI validate backward-compatibility

---

## ADR-08: Data Partitioning

**Status:** Accepted

**Decision:**
- `history_events` and `execution_events` partitioned by month using pg_partman
- `cluster_id` as index prefix on all cluster-scoped tables for efficient cluster-filtered queries
- No cross-cluster joins in hot paths (API request handlers, SSE projectors)
- Old partitions beyond the retention window are detached and archived

---

## ADR-09: Multi-Cluster Network Topology

**Status:** Accepted

**Decision:**
- Hub-spoke model: Pinky control plane (hub) connects **outbound** to managed clusters (spokes)
- No inbound cluster-to-Pinky traffic required
- Observer workers and execution workers connect to cluster API endpoints via the control plane's egress
- VPN/tunnel support is optional, for air-gapped or network-restricted clusters

**Rationale:**
- Outbound-only from hub simplifies firewall rules on managed clusters
- No agent or sidecar deployment required on managed clusters beyond the observer identity

---

## ADR-10: Feature Flags

**Status:** Accepted

**Decision:**
- Database-backed feature flags: simple `feature_flags` table in PostgreSQL
- Schema: `flag_name`, `enabled`, `scope_type` (global / principal / cluster), `scope_id`, `created_at`, `updated_at`
- Per-principal and per-cluster scoping supported
- Flags evaluated at API request time with in-memory cache (~30s TTL)
- No external feature flag service in v1

---

## ADR-11: Backup Strategy

**Status:** Accepted

**Decision:**
- **PostgreSQL:** WAL archiving to object storage, daily base backups, 30-day PITR window
- **Temporal persistence (Postgres-backed):** same backup policy as the primary PostgreSQL instance
- **Redis:** ephemeral by design, no backup required. Session loss = re-login.

---

## ADR-12: DR Policy

**Status:** Accepted

**Decision:**
- **RTO:** 1 hour
- **RPO:** 5 minutes
- Single-region deployment for v1
- Failover: PostgreSQL streaming replication with automated failover (Patroni or equivalent), Redis Sentinel for session store HA
- Multi-region deployment deferred to post-v1

---

## ADR-13: Upgrade Path

**Status:** Accepted

**Decision:**
- Rolling deployments for all components (API, workers, web)
- Database migrations run **before** new code deploys (forward-compatible schema changes only)
- Temporal workflow versioning (patching/get_version) for in-flight workflows during worker rollout
- API backward compatibility within a version
- Deployment order: database migration -> workers -> API -> web
- Rollback: reverse the deployment order; migrations are reversible (ADR-02)

---

## ADR-14: Scale Target Justification

**Status:** Accepted

**Decision:** The architecture supports the stated targets through:

- **Task freshness <10s:** SSE push model delivers projection updates within seconds. Projector lag target is <5s from Temporal event to Postgres write to SSE broadcast.
- **Observation currency:** One observer worker per cluster, polling at 30-second intervals. For 100 clusters, this is 100 concurrent polling loops — well within a single worker pool's capacity.
- **User count (dozens to low hundreds):** At 200 concurrent users with ~3 SSE streams each, 600 connections is trivially handled by a single API process with async I/O.

---

## ADR-15: Observer Identity Provisioning

**Status:** Accepted

**Decision:**
- Automated provisioning via Helm chart deployed to managed clusters
- The Helm chart creates: a read-only `ClusterRole`, `ClusterRoleBinding`, and `ServiceAccount` in a dedicated namespace (`pinky-observer`)
- Token rotation via projected service account tokens: 1-hour TTL, auto-refreshed by the kubelet
- No long-lived static tokens stored in the control plane
- Observer identity health tracked in `ClusterObserverBinding` with last-successful-observation timestamp

---

## ADR-16: LLM Provider Abstraction

**Status:** Accepted

**Decision:**
- Provider-agnostic interface layer: all LLM calls go through an internal abstraction that normalizes request/response formats
- **Primary provider:** Anthropic Claude
- **Fallback provider:** OpenAI
- Provider selection is per model tier, configuration-driven
- Circuit breaker per provider: tracks error rate, trips after configurable threshold, automatic fallback to secondary provider, half-open retry after cooldown

---

## ADR-17: CSRF Implementation

**Status:** Accepted

**Decision:**
- Double-submit cookie pattern: server sets CSRF token in a non-HttpOnly cookie, client sends it in `X-CSRF-Token` header
- `SameSite=Strict` on the session cookie for defense-in-depth
- CSRF token rotated on session rotation
- Token mismatch returns `403 Forbidden` with an explicit error code distinguishable from authz failures

---

## ADR-18: Approval Expiry

**Status:** Accepted

**Decision:**
- Default approval expiry: 4 hours from creation
- Configurable per risk class (very high risk: 1 hour, standard: 4 hours)
- Expired approvals cannot authorize execution; a new approval is required
- Expiry enforced at execution time, not just at creation time
- Invalidation (due to change-set drift) is separate from expiry and takes effect immediately

---

## ADR-19: Cluster Removal Propagation

**Status:** Accepted

**Decision:**
- **Immediate for new actions:** no new tasks, executions, or observations created. Cluster marked `offboarded`.
- **Graceful drain:** 30-minute window for in-flight workflows to complete or checkpoint. Remaining workflows cancelled with `cluster_removed` reason.
- **Task cleanup:** open tasks moved to `done` with `cluster_removed` resolution. Appear in History.
- **History preservation:** all historical records remain available in read-only form indefinitely (subject to retention).
- **Observer teardown:** observer binding revoked, worker stops polling immediately.

---

## ADR-20: External OIDC for Fleet Scale

**Status:** Accepted

**Context:** Per-cluster OAuth at 50+ clusters is operationally unworkable — operators spend their day re-authenticating instead of operating.

**Decision:**
- For deployments with >5 clusters, external OIDC (via OpenShift's external OIDC feature) is a hard requirement for cluster identity bindings
- Per-cluster OAuth login is only acceptable for ≤5 clusters
- One external OIDC provider trusted by all managed clusters gives a single login that provides bindings across the fleet
- The binding acquisition flow detects cluster count and enforces/recommends external OIDC when >5 clusters are registered

---

## ADR-21: Markdown-Driven Definition System

**Status:** Accepted

**Decision:**
- Scanners, tools, skills, pipelines, policies, approval policies, and redaction rules are defined as markdown files with YAML frontmatter
- Frontmatter carries structured config (kind, parameters, auth requirements, conditions). Body carries LLM-readable instructions.
- Definitions ship as files in `definitions/` directory (git-versioned, PR-reviewable)
- Operators can add/override definitions at runtime via API without redeploying — stored in `definitions` DB table
- DB definitions take precedence over filesystem for same `(kind, name)`
- Same pattern as Claude Code skills

**Rationale:**
- Operators can extend without writing Python
- The Brain reads markdown body directly as investigation/tool instructions
- Git-versioned operational policy is auditable and reviewable
- No process overhead — definitions loaded at startup, not sidecar servers

---

## ADR-22: Tool Credential Resolution

**Status:** Accepted

**Decision:**
- Tool MD files declare *what auth they need*, never carry credentials
- Cluster tools declare `authz_class` (observer_read, user_sensitive_read, user_write)
- External service tools declare `service` name (prometheus, datadog, etc.)
- Runtime resolves: tool declaration → execution context (principal, cluster) → binding lookup → decrypt → inject authenticated client
- Tools execute with injected client and never touch raw credentials
- Credential resolution failures produce explicit errors, never silent fallback
- Observer tools cannot be escalated to user-write at runtime
- External service credentials never appear in LLM prompts, evidence, or logs

---

## ADR-23: Domain Event Bus

**Status:** Accepted

**Decision:**
- Every significant state transition emits a `DomainEvent` to an append-only `domain_events` table
- External consumers subscribe via `webhook_subscriptions` table with event type pattern filtering
- Webhook delivery uses a dedicated worker with retry/backoff and `webhook_deliveries` tracking
- Slack/Teams/PagerDuty outbound integrations are webhook subscriptions with built-in formatters, not hardcoded integration code
- `domain_events` table follows same partitioning strategy as `history_events`

**Event types:** `work_item.created`, `work_item.accepted`, `work_item.completed`, `issue.opened`, `issue.resolved`, `approval.requested`, `approval.granted`, `execution.started`, `execution.completed`, `cluster.registered`, `cluster.removed`, `binding.expired`, etc.

---

## ADR-24: Service Bindings

**Status:** Accepted

**Decision:**
- External service tools (Prometheus, Datadog, Grafana) authenticate via **service bindings** — encrypted credentials stored in `service_bindings` table
- Bindings can be global (cluster_id = NULL, shared account) or per-cluster (cluster_id set)
- Tool credential resolution looks up per-cluster binding first, falls back to global
- Credentials encrypted with same AES-256-GCM envelope encryption as cluster bindings (ADR-03)
- Health state tracked per binding with last_check_at timestamp
- Admin-only management via API

---

## ADR-25: API Tokens

**Status:** Accepted

**Decision:**
- Long-lived API tokens for CLI and CI automation, stored in `api_tokens` table
- Tokens are scoped (read, write, admin), hashed (never stored in plaintext), and optionally expiring
- API accepts `Authorization: Bearer <token>` alongside session cookies
- API tokens are separate from product sessions — no CSRF, no cookies
- Token creation/revocation via API and CLI

---

## ADR-15 Addendum: CRD RBAC

**Addendum to ADR-15 (Observer Identity Provisioning):**

- The observer `ClusterRole` is composable via Helm `values.yaml` `observer.additionalRules`
- Scanner manifests declare required `resource_kinds` and `api_groups`
- Observer worker validates RBAC scope at startup via `SelfSubjectAccessReview` for each enabled scanner
- Scanners with insufficient RBAC are marked `degraded` with a reason and a domain event emitted
- No degraded scanner silently skips observations — the gap is visible in cluster health

---

## ADR-16 Addendum: MCP Adapter

**Addendum to ADR-16 (LLM Provider Abstraction):**

- The MD definition system is the primary tool mechanism. MCP is available as a future optional adapter.
- Tool frontmatter may include `adapter: mcp` + `mcp_server_url` + `mcp_tool_name`
- Pinky resolves credentials per `authz_class` / `service`, then invokes MCP tool with authenticated context
- MCP tools appear in the same registry as MD tools — The Brain sees no difference
- v1 ships MD-only. MCP adapter is a documented extension point for post-v1.

---

## Explicitly Rejected Directions

- recreating the old mixed inbox / incident-center model
- preserving `pulse-agent` compatibility by default
- using service accounts for mutations
- using the browser as the holder of raw cluster credentials
- making the product a generic dashboard-builder or toolbox platform in v1

## Deferred Questions

These are intentionally not fixed yet and may be addressed in later design docs:

- whether the product should later enforce separation-of-duties for some action classes
- whether external OIDC remains optional forever or becomes more central later
