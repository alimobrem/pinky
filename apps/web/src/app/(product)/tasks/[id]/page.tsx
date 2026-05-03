"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { ArrowLeft, Brain, User, CheckCircle, Play, Shield, RefreshCw } from "lucide-react";

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
  created_at: string;
}

interface ExecutionEvent {
  id: string;
  event_type: string;
  sequence: number;
  payload: Record<string, unknown>;
  occurred_at: string;
}

const STATUS_COLORS: Record<string, string> = {
  ready: "var(--status-ready)", accepted: "var(--status-accepted)",
  in_progress: "var(--status-in-progress)", blocked: "var(--status-blocked)",
  waiting_for_approval: "var(--status-approval)", done: "var(--status-done)",
};

const PRIORITY_COLORS: Record<string, string> = {
  critical: "var(--priority-critical)", high: "var(--priority-high)",
  medium: "var(--priority-medium)", low: "var(--priority-low)",
};

function confidenceColor(c: number): string {
  if (c >= 0.8) return "var(--status-done)";
  if (c >= 0.5) return "var(--status-in-progress)";
  return "var(--status-blocked)";
}

const VALID_ACTIONS: Record<string, string[]> = {
  ready: ["accept"],
  accepted: ["start"],
  in_progress: ["complete"],
  blocked: ["start"],
  waiting_for_approval: [],
};

export default function TaskDetailPage() {
  const params = useParams();
  const router = useRouter();
  const taskId = params.id as string;

  const [item, setItem] = useState<WorkItem | null>(null);
  const [events, setEvents] = useState<ExecutionEvent[]>([]);
  const [investigation, setInvestigation] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [acting, setActing] = useState(false);

  useEffect(() => {
    Promise.all([
      fetch(`${API}/api/v1/work-items/${taskId}`).then(r => r.ok ? r.json() : null),
      fetch(`${API}/api/v1/executions?work_item_id=${taskId}`).then(r => r.json()).catch(() => ({ items: [] })),
    ]).then(([wi, execs]) => {
      setItem(wi);
      if (execs.items?.length > 0) {
        const execId = execs.items[0].id;
        fetch(`${API}/api/v1/executions/${execId}`).then(r => r.json()).then(ex => {
          if (ex.status) setInvestigation(JSON.stringify(ex, null, 2));
        }).catch(() => {});
      }
      setLoading(false);
    });
  }, [taskId]);

  const doAction = async (action: string) => {
    setActing(true);
    const r = await fetch(`${API}/api/v1/work-items/${taskId}/${action}`, { method: "POST" });
    if (r.ok) {
      const updated = await r.json();
      setItem(updated);
    }
    setActing(false);
  };

  if (loading) {
    return (
      <div>
        <div className="skeleton" style={{ height: 40, width: 300, marginBottom: "var(--space-4)" }} />
        <div className="skeleton" style={{ height: 200, marginBottom: "var(--space-4)" }} />
        <div className="skeleton" style={{ height: 150 }} />
      </div>
    );
  }

  if (!item) {
    return (
      <div style={{ textAlign: "center", padding: "var(--space-16)", color: "var(--text-secondary)" }}>
        Task not found.
      </div>
    );
  }

  const actions = VALID_ACTIONS[item.status] || [];

  return (
    <div>
      {/* Action Bar */}
      <div style={{
        display: "flex", alignItems: "center", justifyContent: "space-between",
        marginBottom: "var(--space-6)",
      }}>
        <button onClick={() => router.push("/tasks")} style={{
          display: "flex", alignItems: "center", gap: "var(--space-2)",
          background: "none", border: "none", color: "var(--text-secondary)",
          fontSize: 13, cursor: "pointer",
        }}>
          <ArrowLeft size={16} />
          Back to Tasks
        </button>

        <div style={{ display: "flex", gap: "var(--space-2)" }}>
          {actions.includes("accept") && (
            <button onClick={() => doAction("accept")} disabled={acting} style={{
              padding: "8px 16px", background: "var(--accent-brand)", color: "#fff",
              border: "none", borderRadius: "var(--radius-md)", fontSize: 13, fontWeight: 600, cursor: "pointer",
            }}>Accept</button>
          )}
          {actions.includes("start") && (
            <button onClick={() => doAction("start")} disabled={acting} style={{
              padding: "8px 16px", background: "var(--accent-brand)", color: "#fff",
              border: "none", borderRadius: "var(--radius-md)", fontSize: 13, fontWeight: 600, cursor: "pointer",
            }}>
              <Play size={14} style={{ marginRight: 4 }} />Start
            </button>
          )}
          {actions.includes("complete") && (
            <button onClick={() => doAction("complete")} disabled={acting} style={{
              padding: "8px 16px", background: "var(--bg-elevated)", color: "var(--text-primary)",
              border: "1px solid var(--border-default)", borderRadius: "var(--radius-md)", fontSize: 13, fontWeight: 600, cursor: "pointer",
            }}>
              <CheckCircle size={14} style={{ marginRight: 4 }} />Complete
            </button>
          )}
        </div>
      </div>

      {/* Header */}
      <div style={{ marginBottom: "var(--space-6)" }}>
        <h1 style={{ fontSize: 22, fontWeight: 700, letterSpacing: "-0.02em", marginBottom: "var(--space-3)" }}>
          {item.title}
        </h1>
        <div style={{ display: "flex", gap: "var(--space-3)", alignItems: "center", flexWrap: "wrap" }}>
          <span style={{ fontSize: 11, padding: "2px 8px", borderRadius: "var(--radius-sm)", background: PRIORITY_COLORS[item.priority], color: "#fff", fontWeight: 600, textTransform: "uppercase" }}>
            {item.priority}
          </span>
          <span style={{ fontSize: 11, padding: "2px 8px", borderRadius: "var(--radius-sm)", background: STATUS_COLORS[item.status], color: "#fff", fontWeight: 600 }}>
            {item.status.replace(/_/g, " ")}
          </span>
          {item.confidence != null && (
            <span className="tabular" style={{ fontSize: 13, fontWeight: 600, color: confidenceColor(item.confidence) }}>
              {Math.round(item.confidence * 100)}% confidence
            </span>
          )}
          {Object.entries(item.labels).map(([k, v]) => (
            <span key={k} style={{ fontSize: 11, padding: "1px 6px", background: "var(--bg-elevated)", borderRadius: "var(--radius-sm)" }}>{k}={v}</span>
          ))}
        </div>
      </div>

      {/* Two-column layout */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 380px", gap: "var(--space-5)", marginBottom: "var(--space-6)" }}>
        {/* Left column */}
        <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-4)" }}>
          {/* Summary */}
          <div style={{ background: "var(--bg-surface)", border: "1px solid var(--border-default)", borderRadius: "var(--radius-lg)", padding: "var(--space-5)" }}>
            <div style={{ fontSize: 12, fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.06em", color: "var(--text-tertiary)", marginBottom: "var(--space-3)", paddingBottom: "var(--space-2)", borderBottom: "1px solid var(--border-subtle)" }}>
              Summary
            </div>
            {item.why_now && (
              <div style={{ marginBottom: "var(--space-4)" }}>
                <div style={{ fontSize: 12, fontWeight: 600, color: "var(--text-tertiary)", marginBottom: "var(--space-1)" }}>Why now</div>
                <div style={{ fontSize: 14, color: "var(--text-primary)", lineHeight: 1.6 }}>{item.why_now}</div>
              </div>
            )}
            <div style={{ fontSize: 12, color: "var(--text-tertiary)" }}>
              Created {new Date(item.created_at).toLocaleString()}
            </div>
          </div>

          {/* Evidence */}
          <div style={{ background: "var(--bg-surface)", border: "1px solid var(--border-default)", borderRadius: "var(--radius-lg)", padding: "var(--space-5)" }}>
            <div style={{ fontSize: 12, fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.06em", color: "var(--text-tertiary)", marginBottom: "var(--space-3)", paddingBottom: "var(--space-2)", borderBottom: "1px solid var(--border-subtle)" }}>
              Evidence
            </div>
            <div style={{ fontSize: 13, color: "var(--text-secondary)", lineHeight: 1.6 }}>
              {investigation ? (
                <pre style={{ fontFamily: "var(--font-mono)", fontSize: 12, whiteSpace: "pre-wrap", wordBreak: "break-word" }}>
                  {investigation}
                </pre>
              ) : (
                <span>No investigation data available yet. Trigger an investigation to gather evidence.</span>
              )}
            </div>
          </div>
        </div>

        {/* Right column */}
        <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-4)" }}>
          {/* Brain Plan */}
          <div style={{
            background: "var(--accent-brain-bg)",
            border: "1px solid var(--border-brain)",
            borderLeft: "3px solid var(--accent-brain)",
            borderRadius: "var(--radius-lg)",
            padding: "var(--space-5)",
            boxShadow: "var(--shadow-brain-glow)",
          }}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "var(--space-3)" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "var(--space-2)", fontSize: 13, fontWeight: 600, color: "var(--accent-brain)" }}>
                <Brain size={16} />
                The Brain recommends
              </div>
              {item.confidence != null && (
                <span className="tabular" style={{ fontSize: 13, fontWeight: 600, color: confidenceColor(item.confidence) }}>
                  {Math.round(item.confidence * 100)}%
                </span>
              )}
            </div>
            <div style={{ fontSize: 14, color: "var(--text-primary)", lineHeight: 1.6 }}>
              {item.recommended_next_step || "No recommendation available yet."}
            </div>
            {item.runbook_url && (
              <div style={{ marginTop: "var(--space-3)", fontSize: 13 }}>
                <a href={item.runbook_url} target="_blank" rel="noopener noreferrer" style={{ color: "var(--accent-brain)" }}>
                  📖 View runbook
                </a>
              </div>
            )}
          </div>

          {/* Trigger Investigation */}
          <button
            onClick={async () => {
              await fetch(`${API}/api/v1/executions?work_item_id=${taskId}&execution_type=investigation`, { method: "POST" });
              router.refresh();
            }}
            style={{
              padding: "10px 16px", background: "var(--bg-surface)",
              border: "1px solid var(--border-brain)", borderRadius: "var(--radius-lg)",
              color: "var(--accent-brain)", fontSize: 13, fontWeight: 600, cursor: "pointer",
              display: "flex", alignItems: "center", justifyContent: "center", gap: "var(--space-2)",
            }}
          >
            <Brain size={16} />
            Run Brain Investigation
          </button>
        </div>
      </div>

      {/* Execution Timeline */}
      <div style={{ background: "var(--bg-surface)", border: "1px solid var(--border-default)", borderRadius: "var(--radius-lg)", padding: "var(--space-5)" }}>
        <div style={{ fontSize: 12, fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.06em", color: "var(--text-tertiary)", marginBottom: "var(--space-3)", paddingBottom: "var(--space-2)", borderBottom: "1px solid var(--border-subtle)" }}>
          Execution Timeline
        </div>
        <div style={{ fontSize: 13, color: "var(--text-secondary)" }}>
          {events.length === 0 ? (
            <span>No execution events yet.</span>
          ) : (
            events.map(e => (
              <div key={e.id} style={{ display: "grid", gridTemplateColumns: "24px 72px 1fr", gap: "var(--space-2)", padding: "var(--space-2) 0", alignItems: "start" }}>
                <div style={{ width: 10, height: 10, borderRadius: "50%", background: "var(--accent-brain)", marginTop: 4, justifySelf: "center" }} />
                <span style={{ fontFamily: "var(--font-mono)", fontSize: 12, color: "var(--text-tertiary)" }}>
                  {new Date(e.occurred_at).toLocaleTimeString()}
                </span>
                <span>{e.event_type}</span>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
