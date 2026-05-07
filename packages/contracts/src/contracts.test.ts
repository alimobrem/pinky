import { describe, expect, it } from "vitest";
import type {
  Principal,
  ClusterRegistryEntry,
  ClusterOnboardingState,
  ClusterBindingStatus,
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
  Investigation,
  Approval,
  ApprovalStatus,
  HistoryEvent,
  PaginatedResponse,
  ErrorResponse,
  SSEEvent,
  SSEHeartbeat,
  AuthProviderConfig,
  Definition,
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
    expect(types).toHaveLength(11);
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
});
