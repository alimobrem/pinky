export type ExecutionStatus =
  | "pending"
  | "running"
  | "waiting_for_approval"
  | "completed"
  | "failed"
  | "timed_out"
  | "cancelled";

export type ExecutionEventType =
  | "started"
  | "progress"
  | "tool_used"
  | "approval_required"
  | "approval_granted"
  | "approval_rejected"
  | "completed"
  | "failed"
  | "verified"
  | "timed_out"
  | "rolled_back";

export interface Execution {
  id: string;
  work_item_id: string | null;
  cluster_id: string;
  cluster_display_name?: string;
  execution_type: string;
  status: ExecutionStatus;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
}

export interface ExecutionEvent {
  event_id: string;
  stream: string;
  aggregate_id: string;
  execution_id: string | null;
  type: ExecutionEventType;
  occurred_at: string;
  sequence: number;
  payload: Record<string, unknown>;
}

export interface TimelineEvent {
  id: string;
  execution_id: string;
  event_type: string;
  sequence: number;
  payload: Record<string, unknown>;
  occurred_at: string;
}

export interface RemediationStep {
  action: string;
  description: string;
  resource_kind: string;
  resource_namespace: string;
  resource_name: string;
  params: Record<string, unknown>;
  risk: "low" | "medium" | "high";
}

export interface Investigation {
  has_investigation: boolean;
  summary?: string;
  root_cause?: string;
  recommended_action?: string;
  confidence?: number;
  tool_calls?: string[];
  created_at?: string;
  remediation_steps?: RemediationStep[];
  manual_commands?: string[];
}

export type ApprovalStatus =
  | "pending"
  | "approved"
  | "rejected"
  | "expired"
  | "invalidated";

export interface Approval {
  id: string;
  execution_id: string;
  approver_id: string | null;
  changeset_digest: string;
  target_resources: Record<string, unknown>[];
  status: ApprovalStatus;
  expires_at: string;
  created_at: string;
}
