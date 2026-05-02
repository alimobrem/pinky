export interface SSEEvent<T = Record<string, unknown>> {
  event_id: string;
  stream: string;
  aggregate_id: string;
  execution_id?: string;
  type: string;
  occurred_at: string;
  sequence: number;
  payload: T;
}

export interface SSEHeartbeat {
  ts: string;
}

export interface SSESnapshotRequired {
  stream: string;
  reason: "buffer_overflow" | "stream_reset";
  fetch_url: string;
}

export interface SSEAuthExpired {
  reason: "session_expired" | "binding_expired";
  cluster_id?: string;
}
