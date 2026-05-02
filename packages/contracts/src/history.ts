export interface HistoryEvent {
  id: string;
  aggregate_type: string;
  aggregate_id: string;
  event_type: string;
  cluster_id: string | null;
  principal_id: string | null;
  payload: Record<string, unknown>;
  occurred_at: string;
}
