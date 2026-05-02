export interface Observation {
  id: string;
  cluster_id: string;
  scanner: string;
  scanner_version: string | null;
  fingerprint: string;
  check_id: string | null;
  severity: "critical" | "high" | "medium" | "low" | "info";
  resource_kind: string | null;
  resource_namespace: string | null;
  resource_name: string | null;
  payload: Record<string, unknown>;
  observed_at: string;
  created_at: string;
}
