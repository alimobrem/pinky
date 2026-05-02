export type IssueStatus = "open" | "investigating" | "resolved" | "suppressed";

export interface Issue {
  id: string;
  cluster_id: string;
  correlation_key: string;
  title: string;
  severity: string;
  status: IssueStatus;
  labels: Record<string, string>;
  annotations: Record<string, string>;
  runbook_url: string | null;
  first_seen_at: string;
  last_seen_at: string;
  resolved_at: string | null;
  suppressed_until: string | null;
  created_at: string;
  updated_at: string;
}
