"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Brain, ChevronRight } from "lucide-react";

const API = "";

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

const STATUS_COLORS: Record<string, string> = {
  ready: "var(--status-ready)",
  accepted: "var(--status-accepted)",
  in_progress: "var(--status-in-progress)",
  blocked: "var(--status-blocked)",
  waiting_for_approval: "var(--status-approval)",
  done: "var(--status-done)",
};

const PRIORITY_COLORS: Record<string, string> = {
  critical: "var(--priority-critical)",
  high: "var(--priority-high)",
  medium: "var(--priority-medium)",
  low: "var(--priority-low)",
};

function confidenceColor(c: number): string {
  if (c >= 0.8) return "var(--status-done)";
  if (c >= 0.5) return "var(--status-in-progress)";
  return "var(--status-blocked)";
}

export default function TasksPage() {
  const [items, setItems] = useState<WorkItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch(`${API}/api/v1/work-items`)
      .then((r) => { if (!r.ok) throw new Error(`${r.status}`); return r.json(); })
      .then((data) => { setItems(data.items || []); setLoading(false); })
      .catch((e) => { setError(e.message); setLoading(false); });
  }, []);

  const counts = {
    ready: items.filter((i) => i.status === "ready").length,
    in_progress: items.filter((i) => i.status === "in_progress" || i.status === "accepted").length,
    blocked: items.filter((i) => i.status === "blocked").length,
    approval: items.filter((i) => i.status === "waiting_for_approval").length,
  };

  return (
    <div>
      <h1 style={{ fontSize: 20, fontWeight: 600, marginBottom: "var(--space-5)", letterSpacing: "-0.01em" }}>Tasks</h1>

      {/* Summary strip */}
      <div style={{ display: "flex", gap: "var(--space-3)", marginBottom: "var(--space-6)" }}>
        {[
          { label: "READY", count: counts.ready, color: "var(--status-ready)" },
          { label: "IN PROGRESS", count: counts.in_progress, color: "var(--status-in-progress)" },
          { label: "BLOCKED", count: counts.blocked, color: "var(--status-blocked)" },
          { label: "NEEDS APPROVAL", count: counts.approval, color: "var(--status-approval)" },
        ].map((s) => (
          <div key={s.label} style={{
            background: "var(--bg-surface)",
            border: "1px solid var(--border-default)",
            borderRadius: "var(--radius-lg)",
            padding: "var(--space-3) var(--space-4)",
            minWidth: 150,
            position: "relative",
            overflow: "hidden",
          }}>
            <div style={{ position: "absolute", top: 0, left: 0, right: 0, height: 2, background: s.color }} />
            <div className="tabular" style={{ fontSize: 28, fontWeight: 700, lineHeight: 1, letterSpacing: "-0.02em" }}>{s.count}</div>
            <div style={{ fontSize: 11, fontWeight: 600, color: "var(--text-tertiary)", marginTop: "var(--space-1)", textTransform: "uppercase", letterSpacing: "0.06em" }}>{s.label}</div>
          </div>
        ))}
      </div>

      {loading && (
        <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-2)" }}>
          {[1, 2, 3].map(i => (
            <div key={i} className="skeleton" style={{ height: 100, borderRadius: "var(--radius-lg)" }} />
          ))}
        </div>
      )}

      {error && (
        <div style={{ padding: "var(--space-4)", background: "rgba(248, 113, 113, 0.08)", border: "1px solid rgba(248, 113, 113, 0.2)", borderRadius: "var(--radius-lg)", color: "#fca5a5" }}>
          Failed to load tasks: {error}
        </div>
      )}

      {!loading && !error && items.length === 0 && (
        <div style={{ display: "flex", flexDirection: "column", alignItems: "center", padding: "var(--space-16) var(--space-6)", textAlign: "center" }}>
          <div style={{ fontFamily: "var(--font-mono)", fontSize: 20, color: "var(--text-tertiary)", marginBottom: "var(--space-6)" }}>( . _ . )</div>
          <div style={{ fontSize: 15, fontWeight: 600, color: "var(--text-primary)", marginBottom: "var(--space-2)" }}>Nothing needs your attention.</div>
          <div style={{ fontSize: 13, color: "var(--text-secondary)", lineHeight: 1.6 }}>The Brain is watching your clusters. If something comes up, it will appear here.</div>
        </div>
      )}

      {!loading && items.length > 0 && (
        <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-2)" }}>
          {items.map((item) => (
            <Link key={item.id} href={`/tasks/${item.id}`} style={{ textDecoration: "none", color: "inherit" }}>
              <div style={{
                background: "var(--bg-surface)",
                border: "1px solid var(--border-default)",
                borderRadius: "var(--radius-lg)",
                padding: "var(--space-4) var(--space-5)",
                borderLeft: `3px solid ${STATUS_COLORS[item.status] || "var(--border-default)"}`,
                cursor: "pointer",
                transition: "background var(--transition-fast), border-color var(--transition-fast)",
              }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "var(--space-2)" }}>
                  <div style={{ fontWeight: 600, fontSize: 15, letterSpacing: "-0.01em" }}>{item.title}</div>
                  <div style={{ display: "flex", gap: "var(--space-2)", flexShrink: 0, alignItems: "center" }}>
                    <span style={{
                      fontSize: 11, padding: "2px 8px", borderRadius: "var(--radius-sm)",
                      background: PRIORITY_COLORS[item.priority] || "var(--priority-low)",
                      color: "#fff", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.04em",
                    }}>{item.priority}</span>
                    <span style={{
                      fontSize: 11, padding: "2px 8px", borderRadius: "var(--radius-sm)",
                      background: STATUS_COLORS[item.status] || "var(--bg-elevated)",
                      color: "#fff", fontWeight: 600,
                    }}>{item.status.replace(/_/g, " ")}</span>
                    <ChevronRight size={16} style={{ color: "var(--text-tertiary)" }} />
                  </div>
                </div>

                {item.why_now && (
                  <div style={{ fontSize: 13, color: "var(--text-secondary)", marginBottom: "var(--space-2)", lineHeight: 1.5 }}>
                    {item.why_now}
                  </div>
                )}

                {item.recommended_next_step && (
                  <div style={{
                    display: "flex", alignItems: "flex-start", gap: "var(--space-2)",
                    fontSize: 13, color: "var(--accent-brain)",
                    background: "var(--accent-brain-bg)", borderRadius: "var(--radius-md)",
                    padding: "var(--space-2) var(--space-3)", marginBottom: "var(--space-2)",
                  }}>
                    <Brain size={14} style={{ marginTop: 2, flexShrink: 0 }} />
                    <span>{item.recommended_next_step}</span>
                  </div>
                )}

                <div style={{ display: "flex", gap: "var(--space-3)", fontSize: 12, color: "var(--text-tertiary)", alignItems: "center" }}>
                  {item.confidence != null && (
                    <span className="tabular" style={{ color: confidenceColor(item.confidence), fontWeight: 600 }}>
                      {Math.round(item.confidence * 100)}%
                    </span>
                  )}
                  {Object.entries(item.labels).map(([k, v]) => (
                    <span key={k} style={{
                      padding: "1px 6px", background: "var(--bg-elevated)",
                      borderRadius: "var(--radius-sm)", fontSize: 11,
                    }}>{k}={v}</span>
                  ))}
                </div>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
