export interface PaginatedResponse<T> {
  items: T[];
  next_cursor: string | null;
  has_more: boolean;
  total_count?: number;
}

export interface ErrorResponse {
  error: {
    code: string;
    message: string;
    details?: Record<string, unknown>;
    request_id: string;
  };
}

export interface PaginationParams {
  cursor?: string;
  limit?: number;
}

export interface WatchSummary {
  since: string;
  signals_processed: number;
  suppressed: number;
  investigating: number;
  tasks_created: number;
  auto_resolved: number;
  workloads_scanned?: number;
  last_scan_at?: string;
  operator_managed_skipped?: number;
}
