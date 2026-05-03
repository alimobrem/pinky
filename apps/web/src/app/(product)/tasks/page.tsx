"use client";

import { useEffect, useState } from "react";

interface WorkItem {
  id: string;
  title: string;
  why_now: string | null;
  recommended_next_step: string | null;
  status: string;
  priority: string;
  confidence: number | null;
  owner_id: string | null;
  labels: Record<string, string>;
  cluster_id: string;
  runbook_url: string | null;
}

const API = "";

const STATUS_COLORS: Record<string, string> = {
  ready: "var(--status-ready)",
  accepted: "var(--status-ready)",
  in_progress: "var(--status-in-progress)",
  blocked: "var(--status-blocked)",
  waiting_for_approval: "var(--status-approval)",
  done: "var(--status-done)",
};

const PRIORITY_COLORS: Record<string, string> = {
  critical: "#ef4444",
  high: "#f97316",
  medium: "#eab308",
  low: "#6b7280",
};

export default function TasksPage() {
  const [items, setItems] = useState<WorkItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch(`${API}/api/v1/work-items`)
      .then((r) => {
        if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
        return r.json();
      })
      .then((data) => {
        setItems(data.items || []);
        setLoading(false);
      })
      .catch((e) => {
        setError(e.message);
        setLoading(false);
      });
  }, []);

  const counts = {
    ready: items.filter((i) => i.status === "ready").length,
    in_progress: items.filter((i) => i.status === "in_progress").length,
    blocked: items.filter((i) => i.status === "blocked").length,
    waiting_for_approval: items.filter((i) => i.status === "waiting_for_approval").length,
  };

  return (
    <div>
      <h1 style={{ fontSize: 20, fontWeight: 600, marginBottom: "var(--space-4)" }}>Tasks</h1>

      <div style={{ display: "flex", gap: "var(--space-3)", marginBottom: "var(--space-6)" }}>
        {[
          { label: "Ready", count: counts.ready, color: "var(--status-ready)" },
          { label: "In Progress", count: counts.in_progress, color: "var(--status-in-progress)" },
          { label: "Blocked", count: counts.blocked, color: "var(--status-blocked)" },
          { label: "Needs Approval", count: counts.waiting_for_approval, color: "var(--status-approval)" },
        ].map((s) => (
          <div key={s.label} style={{
            background: "var(--bg-surface)",
            border: "1px solid var(--border-default)",
            borderRadius: 8,
            padding: "var(--space-3) var(--space-4)",
            minWidth: 140,
          }}>
            <div style={{ fontSize: 24, fontWeight: 700 }}>{s.count}</div>
            <div style={{ fontSize: 13, color: s.color }}>{s.label}</div>
          </div>
        ))}
      </div>

      {loading && (
        <div style={{ padding: "var(--space-8)", textAlign: "center", color: "var(--text-secondary)" }}>
          Loading tasks...
        </div>
      )}

      {error && (
        <div style={{ padding: "var(--space-4)", background: "#2d1b1b", border: "1px solid #7f1d1d", borderRadius: 8, color: "#fca5a5", marginBottom: "var(--space-4)" }}>
          Failed to load tasks: {error}
        </div>
      )}

      {!loading && !error && items.length === 0 && (
        <div style={{ textAlign: "center", padding: "var(--space-8)", color: "var(--text-secondary)" }}>
          No tasks need human attention right now.
        </div>
      )}

      {!loading && items.length > 0 && (
        <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-2)" }}>
          {items.map((item) => (
            <div key={item.id} style={{
              background: "var(--bg-surface)",
              border: "1px solid var(--border-default)",
              borderRadius: 8,
              padding: "var(--space-4)",
              borderLeft: `3px solid ${STATUS_COLORS[item.status] || "var(--border-default)"}`,
            }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "var(--space-2)" }}>
                <div style={{ fontWeight: 600, fontSize: 15 }}>{item.title}</div>
                <div style={{ display: "flex", gap: "var(--space-2)", flexShrink: 0 }}>
                  <span style={{
                    fontSize: 11,
                    padding: "2px 8px",
                    borderRadius: 4,
                    background: PRIORITY_COLORS[item.priority] || "#6b7280",
                    color: "#fff",
                    fontWeight: 600,
                    textTransform: "uppercase",
                  }}>
                    {item.priority}
                  </span>
                  <span style={{
                    fontSize: 11,
                    padding: "2px 8px",
                    borderRadius: 4,
                    background: STATUS_COLORS[item.status] || "var(--bg-elevated)",
                    color: "#fff",
                    fontWeight: 600,
                  }}>
                    {item.status.replace(/_/g, " ")}
                  </span>
                </div>
              </div>

              {item.why_now && (
                <div style={{ fontSize: 13, color: "var(--text-secondary)", marginBottom: "var(--space-2)" }}>
                  {item.why_now}
                </div>
              )}

              {item.recommended_next_step && (
                <div style={{ fontSize: 13, color: "var(--accent-brain)", marginBottom: "var(--space-2)" }}>
                  Next: {item.recommended_next_step}
                </div>
              )}

              <div style={{ display: "flex", gap: "var(--space-3)", fontSize: 12, color: "var(--text-secondary)" }}>
                {item.confidence != null && (
                  <span>Confidence: {Math.round(item.confidence * 100)}%</span>
                )}
                {Object.entries(item.labels).map(([k, v]) => (
                  <span key={k} style={{
                    padding: "1px 6px",
                    background: "var(--bg-elevated)",
                    borderRadius: 3,
                    fontSize: 11,
                  }}>
                    {k}={v}
                  </span>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
