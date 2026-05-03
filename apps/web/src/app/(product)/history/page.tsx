"use client";

import { useEffect, useState } from "react";

const API = "";

interface HistoryEvent {
  id: string;
  aggregate_type: string;
  aggregate_id: string;
  event_type: string;
  cluster_id: string | null;
  payload: Record<string, unknown>;
  occurred_at: string;
}

export default function HistoryPage() {
  const [events, setEvents] = useState<HistoryEvent[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`${API}/api/v1/history`)
      .then(r => r.json())
      .then(data => { setEvents(data.items || []); setLoading(false); })
      .catch(() => setLoading(false));
  }, []);

  return (
    <div>
      <h1 style={{ fontSize: 20, fontWeight: 600, marginBottom: "var(--space-4)" }}>History</h1>

      {loading && <div style={{ padding: "var(--space-8)", textAlign: "center", color: "var(--text-secondary)" }}>Loading...</div>}

      {!loading && events.length === 0 && (
        <div style={{ textAlign: "center", padding: "var(--space-8)", color: "var(--text-secondary)" }}>
          No operational history yet.
        </div>
      )}

      {events.length > 0 && (
        <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-2)" }}>
          {events.map(e => (
            <div key={e.id} style={{
              background: "var(--bg-surface)",
              border: "1px solid var(--border-default)",
              borderRadius: 8,
              padding: "var(--space-3) var(--space-4)",
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
            }}>
              <div>
                <span style={{ fontWeight: 600 }}>{e.event_type}</span>
                <span style={{ color: "var(--text-secondary)", marginLeft: "var(--space-2)", fontSize: 13 }}>
                  {e.aggregate_type}/{e.aggregate_id.slice(0, 8)}
                </span>
              </div>
              <div style={{ fontSize: 12, color: "var(--text-secondary)" }}>
                {new Date(e.occurred_at).toLocaleString()}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
