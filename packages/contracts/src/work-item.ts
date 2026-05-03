export type WorkItemStatus =
  | "ready"
  | "accepted"
  | "in_progress"
  | "blocked"
  | "waiting_for_approval"
  | "done";

export interface WorkItem {
  id: string;
  issue_id: string | null;
  cluster_id: string;
  title: string;
  why_now: string | null;
  recommended_next_step: string | null;
  status: WorkItemStatus;
  owner_id: string | null;
  confidence: number | null;
  priority: "critical" | "high" | "medium" | "low";
  labels: Record<string, string>;
  annotations: Record<string, string>;
  runbook_url: string | null;
  artifact_refs: Record<string, unknown>;
  blocked_reason: string | null;
  created_at: string;
  updated_at: string;
}
