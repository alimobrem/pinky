import { describe, expect, it } from "vitest";
import type {
  Principal,
  ClusterRegistryEntry,
  ClusterOnboardingState,
  ClusterBindingStatus,
  ObserverHealthState,
  ClusterObserverBinding,
  ClusterIdentityBinding,
  ClusterDetail,
  ClusterNode,
  ClusterNamespace,
  K8sEvent,
  Observation,
  Issue,
  IssueStatus,
  WorkItem,
  WorkItemStatus,
  Execution,
  ExecutionStatus,
  ExecutionEvent,
  ExecutionEventType,
  TimelineEvent,
  RemediationStep,
  Investigation,
  Approval,
  ApprovalStatus,
  HistoryEvent,
  PaginatedResponse,
  PaginationParams,
  ErrorResponse,
  WatchSummary,
  SSEEvent,
  SSEHeartbeat,
  SSESnapshotRequired,
  SSEAuthExpired,
  AuthProvider,
  LoginState,
  Session,
  AuthProviderConfig,
  ChartSeries,
  ChartData,
  Definition,
  ApiToken,
  ApiTokenCreateResponse,
  WebhookSubscription,
  PolicyRule,
} from "./index.js";

describe("contracts type instantiation", () => {
  it("Principal fields", () => {
    const p: Principal = {
      id: "uuid-1",
      provider: "openshift",
      subject: "admin",
      display_name: "Admin User",
      email: "admin@test.dev",
      groups: ["pinky-admins"],
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
    };
    expect(p.id).toBe("uuid-1");
    expect(p.groups).toHaveLength(1);
  });

  it("WorkItem status union", () => {
    const statuses: WorkItemStatus[] = [
      "ready",
      "in_progress",
      "blocked",
      "waiting_for_approval",
      "done",
    ];
    expect(statuses).toHaveLength(5);
  });

  it("WorkItem full construction", () => {
    const w: WorkItem = {
      id: "wi-1",
      issue_id: "issue-1",
      cluster_id: "cluster-1",
      title: "Fix OOM",
      why_now: "Pod restarting",
      recommended_next_step: "Increase memory",
      status: "ready",
      owner_id: null,
      owner_display_name: null,
      confidence: 0.85,
      priority: "high",
      labels: { scanner: "pod-health" },
      annotations: {},
      runbook_url: null,
      artifact_refs: {},
      blocked_reason: null,
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
    };
    expect(w.status).toBe("ready");
    expect(w.confidence).toBeGreaterThan(0);
  });

  it("ExecutionEventType union", () => {
    const types: ExecutionEventType[] = [
      "started",
      "progress",
      "command",
      "tool_used",
      "approval_required",
      "approval_granted",
      "approval_rejected",
      "completed",
      "failed",
      "verified",
      "timed_out",
      "rolled_back",
    ];
    expect(types).toHaveLength(12);
  });

  it("IssueStatus union", () => {
    const statuses: IssueStatus[] = [
      "open",
      "investigating",
      "resolved",
      "suppressed",
    ];
    expect(statuses).toHaveLength(4);
  });

  it("PaginatedResponse generic", () => {
    const response: PaginatedResponse<WorkItem> = {
      items: [],
      next_cursor: null,
      has_more: false,
    };
    expect(response.items).toHaveLength(0);
    expect(response.has_more).toBe(false);
  });

  it("ErrorResponse structure", () => {
    const err: ErrorResponse = {
      error: {
        code: "not_found",
        message: "Work item not found",
        request_id: "req-123",
      },
    };
    expect(err.error.code).toBe("not_found");
  });

  it("SSEEvent generic", () => {
    const event: SSEEvent<{ status: string }> = {
      event_id: "evt-1",
      stream: "work-items",
      aggregate_id: "wi-1",
      type: "status_changed",
      occurred_at: "2026-01-01T00:00:00Z",
      sequence: 1,
      payload: { status: "in_progress" },
    };
    expect(event.payload.status).toBe("in_progress");
  });

  it("ClusterOnboardingState values", () => {
    const states: ClusterOnboardingState[] = [
      "pending",
      "provisioning",
      "ready",
      "degraded",
      "offboarding",
      "offboarded",
    ];
    expect(states).toHaveLength(6);
  });

  it("Investigation structure", () => {
    const inv: Investigation = {
      has_investigation: true,
      summary: "OOM detected",
      root_cause: "Memory limit too low",
      recommended_action: "Increase to 512Mi",
      confidence: 0.85,
      tool_calls: [],
      created_at: "2026-01-01T00:00:00Z",
    };
    expect(inv.has_investigation).toBe(true);
  });

  it("Definition structure", () => {
    const def: Definition = {
      id: "def-1",
      kind: "scanner",
      name: "pod-health",
      version: "1.0.0",
      enabled: true,
      frontmatter: { timeout: 30 },
      body: "# Scanner body",
      source: "database",
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
    };
    expect(def.kind).toBe("scanner");
  });

  it("ChartSeries and ChartData bar", () => {
    const series: ChartSeries = { key: "cpu", label: "CPU", color: "#f00" };
    const chart: ChartData = {
      type: "bar",
      title: "Top pods",
      xKey: "pod",
      data: [{ pod: "nginx", cpu: 85 }],
      series: [series],
    };
    expect(chart.type).toBe("bar");
    expect(chart.series).toHaveLength(1);
  });

  it("ChartData line", () => {
    const chart: ChartData = {
      type: "line",
      title: "CPU over time",
      xKey: "ts",
      data: [{ ts: "10:00", value: 42 }],
      series: [{ key: "value", label: "CPU %", color: "#00f" }],
    };
    expect(chart.type).toBe("line");
  });

  it("SSEHeartbeat", () => {
    const hb: SSEHeartbeat = { ts: "2026-01-01T00:00:00Z" };
    expect(hb.ts).toBeTruthy();
  });

  it("SSESnapshotRequired", () => {
    const snap: SSESnapshotRequired = {
      stream: "work-items",
      reason: "buffer_overflow",
      fetch_url: "/api/v1/work-items",
    };
    expect(snap.reason).toBe("buffer_overflow");

    const reset: SSESnapshotRequired = {
      stream: "issues",
      reason: "stream_reset",
      fetch_url: "/api/v1/issues",
    };
    expect(reset.reason).toBe("stream_reset");
  });

  it("SSEAuthExpired", () => {
    const expired: SSEAuthExpired = { reason: "session_expired" };
    expect(expired.reason).toBe("session_expired");
    expect(expired.cluster_id).toBeUndefined();

    const binding: SSEAuthExpired = {
      reason: "binding_expired",
      cluster_id: "cluster-1",
    };
    expect(binding.cluster_id).toBe("cluster-1");
  });

  it("WatchSummary", () => {
    const summary: WatchSummary = {
      since: "2026-01-01T00:00:00Z",
      signals_processed: 100,
      suppressed: 10,
      investigating: 5,
      tasks_created: 3,
      auto_resolved: 2,
    };
    expect(summary.signals_processed).toBe(100);
    expect(summary.workloads_scanned).toBeUndefined();
  });

  it("WatchSummary with optional fields", () => {
    const full: WatchSummary = {
      since: "2026-01-01T00:00:00Z",
      signals_processed: 50,
      suppressed: 5,
      investigating: 2,
      tasks_created: 1,
      auto_resolved: 0,
      workloads_scanned: 200,
      last_scan_at: "2026-01-01T12:00:00Z",
      operator_managed_skipped: 10,
    };
    expect(full.workloads_scanned).toBe(200);
    expect(full.operator_managed_skipped).toBe(10);
  });

  it("PaginationParams", () => {
    const params: PaginationParams = { cursor: "abc", limit: 25 };
    expect(params.limit).toBe(25);

    const empty: PaginationParams = {};
    expect(empty.cursor).toBeUndefined();
  });

  it("PaginatedResponse with total_count", () => {
    const r: PaginatedResponse<{ id: string }> = {
      items: [{ id: "1" }],
      next_cursor: "cur",
      has_more: true,
      total_count: 42,
    };
    expect(r.total_count).toBe(42);
  });

  it("ErrorResponse with details", () => {
    const err: ErrorResponse = {
      error: {
        code: "validation_error",
        message: "Invalid input",
        details: { field: "name" },
        request_id: "req-456",
      },
    };
    expect(err.error.details?.field).toBe("name");
  });

  it("AuthProvider union", () => {
    const providers: AuthProvider[] = ["openshift", "oidc"];
    expect(providers).toHaveLength(2);
  });

  it("LoginState union", () => {
    const states: LoginState[] = [
      "unauthenticated",
      "authenticating",
      "login_failed",
      "signed_in",
    ];
    expect(states).toHaveLength(4);
  });

  it("Session structure", () => {
    const s: Session = {
      id: "sess-1",
      principal_id: "p-1",
      idle_expires_at: "2026-01-02T00:00:00Z",
      absolute_expires_at: "2026-01-03T00:00:00Z",
      created_at: "2026-01-01T00:00:00Z",
    };
    expect(s.principal_id).toBe("p-1");
  });

  it("AuthProviderConfig", () => {
    const cfg: AuthProviderConfig = {
      provider: "openshift",
      display_name: "OpenShift",
      enabled: true,
    };
    expect(cfg.enabled).toBe(true);
  });

  it("ClusterBindingStatus union", () => {
    const statuses: ClusterBindingStatus[] = [
      "missing",
      "valid",
      "expiring",
      "expired",
      "revoked",
    ];
    expect(statuses).toHaveLength(5);
  });

  it("ObserverHealthState union", () => {
    const states: ObserverHealthState[] = [
      "unknown",
      "healthy",
      "degraded",
      "unhealthy",
    ];
    expect(states).toHaveLength(4);
  });

  it("ClusterRegistryEntry full", () => {
    const entry: ClusterRegistryEntry = {
      id: "c-1",
      display_name: "Production",
      api_endpoint: "https://api.prod.example.com:6443",
      fleet_identifier: "fleet-east",
      onboarding_state: "ready",
      offboarding_state: null,
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
    };
    expect(entry.display_name).toBe("Production");
    expect(entry.fleet_identifier).toBe("fleet-east");
  });

  it("ClusterObserverBinding", () => {
    const b: ClusterObserverBinding = {
      id: "ob-1",
      cluster_id: "c-1",
      auth_method: "token",
      health_state: "healthy",
      last_observation_at: "2026-01-01T12:00:00Z",
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
    };
    expect(b.health_state).toBe("healthy");
  });

  it("ClusterIdentityBinding with nulls", () => {
    const b: ClusterIdentityBinding = {
      id: "ib-1",
      principal_id: "p-1",
      cluster_id: "c-1",
      cluster_username: null,
      cluster_groups: [],
      binding_method: "oauth",
      status: "valid",
      expires_at: null,
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
    };
    expect(b.cluster_username).toBeNull();
    expect(b.expires_at).toBeNull();
  });

  it("ClusterDetail extends ClusterRegistryEntry", () => {
    const d: ClusterDetail = {
      id: "c-1",
      display_name: "Staging",
      api_endpoint: "https://api.stage.example.com:6443",
      fleet_identifier: null,
      onboarding_state: "ready",
      offboarding_state: null,
      observer_health: "healthy",
      last_observation_at: "2026-01-01T12:00:00Z",
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
    };
    expect(d.observer_health).toBe("healthy");
  });

  it("ClusterNode with taints", () => {
    const node: ClusterNode = {
      name: "node-1",
      status: "Ready",
      roles: ["master", "worker"],
      kubelet_version: "v1.28.0",
      capacity: { cpu: "4", memory: "16Gi" },
      allocatable: { cpu: "3800m", memory: "15Gi" },
      taints: [{ key: "node-role.kubernetes.io/master", effect: "NoSchedule" }],
      created_at: "2026-01-01T00:00:00Z",
    };
    expect(node.taints).toHaveLength(1);
    expect(node.taints[0].value).toBeUndefined();
  });

  it("ClusterNamespace", () => {
    const ns: ClusterNamespace = {
      name: "default",
      status: "Active",
      created_at: "2026-01-01T00:00:00Z",
    };
    expect(ns.status).toBe("Active");
  });

  it("K8sEvent", () => {
    const evt: K8sEvent = {
      reason: "OOMKilled",
      message: "Container exceeded memory limit",
      type: "Warning",
      involved_object: { kind: "Pod", name: "nginx-abc", namespace: "default" },
      last_timestamp: null,
      count: 3,
    };
    expect(evt.count).toBe(3);
    expect(evt.last_timestamp).toBeNull();
  });

  it("Observation full", () => {
    const obs: Observation = {
      id: "obs-1",
      cluster_id: "c-1",
      scanner: "pod-health",
      scanner_version: "1.0.0",
      fingerprint: "fp-abc",
      check_id: "restart-loop",
      severity: "high",
      resource_kind: "Pod",
      resource_namespace: "default",
      resource_name: "nginx-abc",
      payload: { restarts: 5 },
      observed_at: "2026-01-01T12:00:00Z",
      created_at: "2026-01-01T12:00:00Z",
    };
    expect(obs.severity).toBe("high");
  });

  it("Issue full", () => {
    const issue: Issue = {
      id: "issue-1",
      cluster_id: "c-1",
      correlation_key: "pod-health:default:nginx",
      title: "Pod crash loop",
      severity: "high",
      status: "open",
      labels: { scanner: "pod-health" },
      annotations: {},
      runbook_url: null,
      first_seen_at: "2026-01-01T00:00:00Z",
      last_seen_at: "2026-01-01T12:00:00Z",
      resolved_at: null,
      suppressed_until: null,
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T12:00:00Z",
    };
    expect(issue.status).toBe("open");
    expect(issue.resolved_at).toBeNull();
  });

  it("ExecutionStatus union", () => {
    const statuses: ExecutionStatus[] = [
      "pending",
      "running",
      "waiting_for_approval",
      "completed",
      "failed",
      "timed_out",
      "cancelled",
    ];
    expect(statuses).toHaveLength(7);
  });

  it("Execution full", () => {
    const exec: Execution = {
      id: "exec-1",
      work_item_id: "wi-1",
      cluster_id: "c-1",
      execution_type: "remediation",
      status: "running",
      started_at: "2026-01-01T12:00:00Z",
      completed_at: null,
      created_at: "2026-01-01T12:00:00Z",
    };
    expect(exec.status).toBe("running");
  });

  it("ExecutionEvent", () => {
    const evt: ExecutionEvent = {
      event_id: "ee-1",
      stream: "execution",
      aggregate_id: "exec-1",
      execution_id: "exec-1",
      type: "command",
      occurred_at: "2026-01-01T12:00:00Z",
      sequence: 1,
      payload: { command: "oc scale deploy/nginx --replicas=3" },
    };
    expect(evt.type).toBe("command");
  });

  it("TimelineEvent", () => {
    const evt: TimelineEvent = {
      id: "tl-1",
      execution_id: "exec-1",
      event_type: "progress",
      sequence: 2,
      payload: { message: "Scaling deployment" },
      occurred_at: "2026-01-01T12:01:00Z",
    };
    expect(evt.sequence).toBe(2);
  });

  it("RemediationStep", () => {
    const step: RemediationStep = {
      action: "scale",
      description: "Scale nginx to 3 replicas",
      resource_kind: "Deployment",
      resource_namespace: "default",
      resource_name: "nginx",
      params: { replicas: 3 },
      risk: "low",
    };
    expect(step.risk).toBe("low");
  });

  it("Investigation with remediation_steps", () => {
    const inv: Investigation = {
      has_investigation: true,
      summary: "OOM detected",
      remediation_steps: [
        {
          action: "patch",
          description: "Increase memory",
          resource_kind: "Deployment",
          resource_namespace: "default",
          resource_name: "nginx",
          params: { memory: "512Mi" },
          risk: "medium",
        },
      ],
      manual_commands: ["oc set resources deploy/nginx -c nginx --limits=memory=512Mi"],
    };
    expect(inv.remediation_steps).toHaveLength(1);
    expect(inv.manual_commands).toHaveLength(1);
  });

  it("ApprovalStatus union", () => {
    const statuses: ApprovalStatus[] = [
      "pending",
      "approved",
      "rejected",
      "expired",
      "invalidated",
    ];
    expect(statuses).toHaveLength(5);
  });

  it("Approval full", () => {
    const a: Approval = {
      id: "apr-1",
      execution_id: "exec-1",
      approver_id: null,
      changeset_digest: "sha256:abc",
      target_resources: [{ kind: "Deployment", name: "nginx" }],
      status: "pending",
      expires_at: "2026-01-02T00:00:00Z",
      created_at: "2026-01-01T12:00:00Z",
    };
    expect(a.status).toBe("pending");
    expect(a.approver_id).toBeNull();
  });

  it("HistoryEvent full", () => {
    const evt: HistoryEvent = {
      id: "he-1",
      aggregate_type: "work_item",
      aggregate_id: "wi-1",
      event_type: "status_changed",
      cluster_id: "c-1",
      principal_id: "p-1",
      payload: { from: "ready", to: "in_progress" },
      occurred_at: "2026-01-01T12:00:00Z",
      aggregate_title: "Fix OOM",
      principal_display_name: "Admin",
      description: "Status changed to in_progress",
    };
    expect(evt.event_type).toBe("status_changed");
  });

  it("HistoryEvent with null optionals", () => {
    const evt: HistoryEvent = {
      id: "he-2",
      aggregate_type: "issue",
      aggregate_id: "issue-1",
      event_type: "created",
      cluster_id: null,
      principal_id: null,
      payload: {},
      occurred_at: "2026-01-01T00:00:00Z",
    };
    expect(evt.cluster_id).toBeNull();
    expect(evt.aggregate_title).toBeUndefined();
  });

  it("ApiToken", () => {
    const token: ApiToken = {
      id: "tok-1",
      name: "CI Token",
      scopes: ["read", "write"],
      last_used_at: null,
      expires_at: "2026-12-31T00:00:00Z",
      created_at: "2026-01-01T00:00:00Z",
    };
    expect(token.scopes).toHaveLength(2);
    expect(token.last_used_at).toBeNull();
  });

  it("ApiTokenCreateResponse extends ApiToken", () => {
    const resp: ApiTokenCreateResponse = {
      id: "tok-1",
      name: "CI Token",
      scopes: ["read"],
      last_used_at: null,
      expires_at: null,
      created_at: "2026-01-01T00:00:00Z",
      token: "pk_live_abc123",
    };
    expect(resp.token).toBe("pk_live_abc123");
  });

  it("WebhookSubscription", () => {
    const sub: WebhookSubscription = {
      id: "wh-1",
      name: "Slack alerts",
      url: "https://hooks.slack.com/services/xxx",
      event_patterns: ["issue.created", "execution.completed"],
      formatter: "slack",
      enabled: true,
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
    };
    expect(sub.event_patterns).toHaveLength(2);
  });

  it("PolicyRule with null description", () => {
    const rule: PolicyRule = {
      id: "pr-1",
      name: "Auto-investigate critical",
      description: null,
      priority: 100,
      conditions: { severity: "critical" },
      action: { type: "investigate" },
      enabled: true,
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
    };
    expect(rule.description).toBeNull();
    expect(rule.priority).toBe(100);
  });

  it("WorkItem priority union", () => {
    const priorities: WorkItem["priority"][] = ["critical", "high", "medium", "low"];
    expect(priorities).toHaveLength(4);
  });

  it("Definition source union", () => {
    const sources: Definition["source"][] = ["filesystem", "database"];
    expect(sources).toHaveLength(2);
  });
});
