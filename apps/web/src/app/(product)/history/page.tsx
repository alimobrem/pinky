"use client";

import { useEffect, useState } from "react";
import { Clock, Filter } from "lucide-react";

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

const TYPE_COLORS: Record<string, string> = {
  "work_item": "var(--accent-brand)",
  "execution": "var(--accent-brain)",
  "approval": "var(--status-approval)",
  "cluster": "var(--status-ready)",
  "issue": "var(--status-in-progress)",
};

export default function HistoryPage() {
  const [events, setEvents] = useState<HistoryEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [typeFilter, setTypeFilter] = useState("");

  useEffect(() => {
    fetch(`${API}/api/v1/history`)
      .then(r => { if (!r.ok) throw new Error(`${r.status}`); return r.json(); })
      .then(data => { setEvents(data.items || []); setLoading(false); })
      .catch(e => { setError(`Failed to load history: ${e.message}`); setLoading(false); });
  }, []);

  const filtered = typeFilter ? events.filter(e => e.aggregate_type === typeFilter) : events;
  const types = [...new Set(events.map(e => e.aggregate_type))];

  return (
    <div>
      <div style={{ display: "flex", alignItems: "center", gap: "var(--space-3)", marginBottom: "var(--space-5)" }}>
        <Clock size={20} style={{ color: "var(--text-tertiary)" }} />
        <h1 style={{ fontSize: 20, fontWeight: 600, letterSpacing: "-0.01em" }}>History</h1>
      </div>

      {/* Filter bar */}
      <div style={{ display: "flex", gap: "var(--space-3)", marginBottom: "var(--space-4)", alignItems: "center" }}>
        <Filter size={14} style={{ color: "var(--text-tertiary)" }} />
        <select value={typeFilter} onChange={e => setTypeFilter(e.target.value)} style={{
          background: "var(--bg-elevated)", color: "var(--text-primary)", border: "1px solid var(--border-default)",
          borderRadius: "var(--radius-md)", padding: "4px 8px", fontSize: 12,
        }}>
          <option value="">All Types</option>
          {types.map(t => <option key={t} value={t}>{t}</option>)}
        </select>
        <span style={{ marginLeft: "auto", fontSize: 12, color: "var(--text-tertiary)" }}>{filtered.length} events</span>
      </div>

      {error && (
        <div style={{
          padding: "var(--space-3) var(--space-4)", marginBottom: "var(--space-4)",
          background: "rgba(248, 113, 113, 0.1)", border: "1px solid rgba(248, 113, 113, 0.3)",
          borderRadius: "var(--radius-md)", color: "var(--status-blocked)", fontSize: 13,
        }}>{error}</div>
      )}

      {loading && (
        <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-2)" }}>
          {[1, 2, 3].map(i => <div key={i} className="skeleton" style={{ height: 48, borderRadius: "var(--radius-lg)" }} />)}
        </div>
      )}

      {!loading && filtered.length === 0 && (
        <div style={{ display: "flex", flexDirection: "column", alignItems: "center", padding: "var(--space-16) var(--space-6)", textAlign: "center" }}>
          <div style={{ fontFamily: "var(--font-mono)", fontSize: 20, color: "var(--text-tertiary)", marginBottom: "var(--space-6)" }}>(empty)</div>
          <div style={{ fontSize: 15, fontWeight: 600, marginBottom: "var(--space-2)" }}>No operational history yet.</div>
          <div style={{ fontSize: 13, color: "var(--text-secondary)", lineHeight: 1.6 }}>Completed tasks, remediations, and approvals will appear here over time.</div>
        </div>
      )}

      {filtered.length > 0 && (
        <div style={{ display: "flex", flexDirection: "column" }}>
          {filtered.map((e, i) => (
            <div key={e.id} style={{
              display: "grid", gridTemplateColumns: "10px 140px 120px 1fr",
              gap: "var(--space-3)", padding: "var(--space-3) var(--space-4)",
              borderBottom: i < filtered.length - 1 ? "1px solid var(--border-subtle)" : "none",
              alignItems: "center",
            }}>
              <div style={{
                width: 8, height: 8, borderRadius: "50%",
                background: TYPE_COLORS[e.aggregate_type] || "var(--text-tertiary)",
              }} />
              <span style={{ fontFamily: "var(--font-mono)", fontSize: 12, color: "var(--text-tertiary)", fontVariantNumeric: "tabular-nums" }}>
                {new Date(e.occurred_at).toLocaleString()}
              </span>
              <span style={{
                fontSize: 11, fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.04em",
                color: TYPE_COLORS[e.aggregate_type] || "var(--text-secondary)",
              }}>{e.event_type}</span>
              <span style={{ fontSize: 13, color: "var(--text-secondary)" }}>
                {e.aggregate_type}/{e.aggregate_id.slice(0, 8)}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
