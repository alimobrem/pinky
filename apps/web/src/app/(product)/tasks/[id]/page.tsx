"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { ArrowLeft, Brain, CheckCircle, Play, Clock, AlertTriangle, ChevronDown, ChevronRight, Zap } from "lucide-react";

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

interface Investigation {
  has_investigation: boolean;
  summary?: string;
  root_cause?: string;
  recommended_action?: string;
  confidence?: number;
  tool_calls?: string[];
  evidence_hash?: string;
  created_at?: string;
}

interface TimelineEvent {
  id: string;
  execution_id: string;
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

function confidenceLabel(c: number): string {
  if (c >= 0.8) return "High confidence";
  if (c >= 0.5) return "Moderate confidence";
  return "Low confidence";
}

const VALID_ACTIONS: Record<string, string[]> = {
  ready: ["accept"], accepted: ["start"], in_progress: ["complete"], blocked: ["start"],
};

const EVENT_ICONS: Record<string, string> = {
  started: "🚀", completed: "✅", failed: "❌", investigation_completed: "🔍",
  approval_required: "🛡️", approval_granted: "✅", approval_rejected: "❌",
  verified: "✓", timed_out: "⏰",
};

export default function TaskDetailPage() {
  const params = useParams();
  const router = useRouter();
  const taskId = params.id as string;

  const [item, setItem] = useState<WorkItem | null>(null);
  const [investigation, setInvestigation] = useState<Investigation | null>(null);
  const [events, setEvents] = useState<TimelineEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [acting, setActing] = useState(false);
  const [showReasoning, setShowReasoning] = useState(false);

  useEffect(() => {
    Promise.all([
      fetch(`${API}/api/v1/work-items/${taskId}`).then(r => r.ok ? r.json() : null),
      fetch(`${API}/api/v1/work-items/${taskId}/investigation`).then(r => r.json()).catch(() => ({ has_investigation: false })),
      fetch(`${API}/api/v1/work-items/${taskId}/events`).then(r => r.json()).catch(() => ({ items: [] })),
    ]).then(([wi, inv, evts]) => {
      setItem(wi);
      setInvestigation(inv);
      setEvents(evts.items || []);
      setLoading(false);
    });
  }, [taskId]);

  const doAction = async (action: string) => {
    setActing(true);
    const r = await fetch(`${API}/api/v1/work-items/${taskId}/${action}`, { method: "POST" });
    if (r.ok) setItem(await r.json());
    setActing(false);
  };

  const triggerInvestigation = async () => {
    setActing(true);
    await fetch(`${API}/api/v1/executions?work_item_id=${taskId}&execution_type=investigation`, { method: "POST" });
    setTimeout(async () => {
      const [inv, evts] = await Promise.all([
        fetch(`${API}/api/v1/work-items/${taskId}/investigation`).then(r => r.json()),
        fetch(`${API}/api/v1/work-items/${taskId}/events`).then(r => r.json()),
      ]);
      setInvestigation(inv);
      setEvents(evts.items || []);
      setActing(false);
    }, 2000);
  };

  if (loading) return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-4)" }}>
      {[1, 2, 3].map(i => <div key={i} className="skeleton" style={{ height: i === 1 ? 60 : 180, borderRadius: "var(--radius-lg)" }} />)}
    </div>
  );

  if (!item) return (
    <div style={{ textAlign: "center", padding: "var(--space-16)", color: "var(--text-secondary)" }}>Task not found.</div>
  );

  const actions = VALID_ACTIONS[item.status] || [];
  const inv = investigation?.has_investigation ? investigation : null;

  return (
    <div>
      {/* Action Bar */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "var(--space-5)" }}>
        <button onClick={() => router.push("/tasks")} style={{
          display: "flex", alignItems: "center", gap: "var(--space-2)",
          background: "none", border: "none", color: "var(--text-secondary)", fontSize: 13, cursor: "pointer",
        }}>
          <ArrowLeft size={16} /> Back to Tasks
        </button>
        <div style={{ display: "flex", gap: "var(--space-2)" }}>
          {actions.includes("accept") && (
            <button onClick={() => doAction("accept")} disabled={acting} style={{
              padding: "8px 20px", background: "var(--accent-brand)", color: "#fff",
              border: "none", borderRadius: "var(--radius-md)", fontSize: 13, fontWeight: 600, cursor: "pointer",
            }}>Accept</button>
          )}
          {actions.includes("start") && (
            <button onClick={() => doAction("start")} disabled={acting} style={{
              display: "flex", alignItems: "center", gap: 4,
              padding: "8px 20px", background: "var(--accent-brand)", color: "#fff",
              border: "none", borderRadius: "var(--radius-md)", fontSize: 13, fontWeight: 600, cursor: "pointer",
            }}><Play size={14} />Start</button>
          )}
          {actions.includes("complete") && (
            <button onClick={() => doAction("complete")} disabled={acting} style={{
              display: "flex", alignItems: "center", gap: 4,
              padding: "8px 20px", background: "var(--bg-elevated)", color: "var(--text-primary)",
              border: "1px solid var(--border-default)", borderRadius: "var(--radius-md)", fontSize: 13, fontWeight: 600, cursor: "pointer",
            }}><CheckCircle size={14} />Complete</button>
          )}
        </div>
      </div>

      {/* Header */}
      <div style={{ marginBottom: "var(--space-6)" }}>
        <h1 style={{ fontSize: 24, fontWeight: 700, letterSpacing: "-0.02em", marginBottom: "var(--space-3)", lineHeight: 1.2 }}>{item.title}</h1>
        <div style={{ display: "flex", gap: "var(--space-3)", alignItems: "center", flexWrap: "wrap" }}>
          <span style={{ fontSize: 11, padding: "2px 8px", borderRadius: "var(--radius-sm)", background: PRIORITY_COLORS[item.priority], color: "#fff", fontWeight: 600, textTransform: "uppercase" }}>{item.priority}</span>
          <span style={{ fontSize: 11, padding: "2px 8px", borderRadius: "var(--radius-sm)", background: STATUS_COLORS[item.status], color: "#fff", fontWeight: 600 }}>{item.status.replace(/_/g, " ")}</span>
          {Object.entries(item.labels).map(([k, v]) => (
            <span key={k} style={{ fontSize: 11, padding: "1px 6px", background: "var(--bg-elevated)", borderRadius: "var(--radius-sm)", color: "var(--text-secondary)" }}>{k}={v}</span>
          ))}
        </div>
      </div>

      {/* Two-column layout */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 400px", gap: "var(--space-5)", marginBottom: "var(--space-6)" }}>
        {/* Left column */}
        <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-4)" }}>
          {/* Summary */}
          <section style={{ background: "var(--bg-surface)", border: "1px solid var(--border-default)", borderRadius: "var(--radius-lg)", padding: "var(--space-5)" }}>
            <h2 style={{ fontSize: 12, fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.06em", color: "var(--text-tertiary)", marginBottom: "var(--space-3)", paddingBottom: "var(--space-2)", borderBottom: "1px solid var(--border-subtle)" }}>Summary</h2>
            {item.why_now && (
              <div style={{ marginBottom: "var(--space-4)" }}>
                <div style={{ fontSize: 12, fontWeight: 600, color: "var(--text-tertiary)", marginBottom: "var(--space-1)" }}>Why now</div>
                <div style={{ fontSize: 14, lineHeight: 1.6 }}>{item.why_now}</div>
              </div>
            )}
            <div style={{ fontSize: 12, color: "var(--text-tertiary)" }}>Created {new Date(item.created_at).toLocaleString()}</div>
          </section>

          {/* Investigation Results */}
          {inv && (
            <section style={{ background: "var(--bg-surface)", border: "1px solid var(--border-default)", borderRadius: "var(--radius-lg)", padding: "var(--space-5)" }}>
              <h2 style={{ fontSize: 12, fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.06em", color: "var(--text-tertiary)", marginBottom: "var(--space-3)", paddingBottom: "var(--space-2)", borderBottom: "1px solid var(--border-subtle)" }}>
                <span style={{ display: "flex", alignItems: "center", gap: "var(--space-2)" }}>
                  <Brain size={14} style={{ color: "var(--accent-brain)" }} />
                  Investigation Results
                </span>
              </h2>

              {inv.summary && (
                <div style={{ fontSize: 14, lineHeight: 1.7, marginBottom: "var(--space-4)", whiteSpace: "pre-wrap" }}>
                  {inv.summary}
                </div>
              )}

              {inv.root_cause && inv.root_cause !== inv.summary && (
                <div style={{ marginBottom: "var(--space-4)" }}>
                  <button
                    onClick={() => setShowReasoning(!showReasoning)}
                    style={{
                      display: "flex", alignItems: "center", gap: "var(--space-2)",
                      background: "none", border: "none", color: "var(--accent-brain)",
                      fontSize: 13, fontWeight: 600, cursor: "pointer", padding: 0,
                    }}
                  >
                    {showReasoning ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                    View full analysis
                  </button>
                  {showReasoning && (
                    <div style={{
                      marginTop: "var(--space-3)", paddingTop: "var(--space-3)",
                      borderTop: "1px solid var(--border-brain)",
                      fontSize: 13, color: "var(--text-secondary)", lineHeight: 1.7,
                      whiteSpace: "pre-wrap",
                    }}>
                      {inv.root_cause}
                    </div>
                  )}
                </div>
              )}

              <div style={{ fontSize: 12, color: "var(--text-tertiary)" }}>
                Investigated {inv.created_at ? new Date(inv.created_at).toLocaleString() : "recently"}
              </div>
            </section>
          )}

          {/* No investigation yet */}
          {!inv && (
            <section style={{ background: "var(--bg-surface)", border: "1px solid var(--border-default)", borderRadius: "var(--radius-lg)", padding: "var(--space-5)", textAlign: "center" }}>
              <Brain size={24} style={{ color: "var(--text-tertiary)", marginBottom: "var(--space-3)" }} />
              <div style={{ fontSize: 14, color: "var(--text-secondary)", marginBottom: "var(--space-3)" }}>No investigation data yet.</div>
              <div style={{ fontSize: 13, color: "var(--text-tertiary)" }}>Trigger an investigation to have The Brain analyze this issue.</div>
            </section>
          )}
        </div>

        {/* Right column */}
        <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-4)" }}>
          {/* Brain Plan */}
          <div style={{
            background: "var(--accent-brain-bg)", border: "1px solid var(--border-brain)",
            borderLeft: "3px solid var(--accent-brain)", borderRadius: "var(--radius-lg)",
            padding: "var(--space-5)", boxShadow: "var(--shadow-brain-glow)",
          }}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "var(--space-3)" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "var(--space-2)", fontSize: 13, fontWeight: 600, color: "var(--accent-brain)" }}>
                <Brain size={16} /> The Brain recommends
              </div>
              {(inv?.confidence ?? item.confidence) != null && (
                <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end" }}>
                  <span className="tabular" style={{ fontSize: 18, fontWeight: 700, color: confidenceColor((inv?.confidence ?? item.confidence)!) }}>
                    {Math.round((inv?.confidence ?? item.confidence)! * 100)}%
                  </span>
                  <span style={{ fontSize: 11, color: "var(--text-tertiary)" }}>
                    {confidenceLabel((inv?.confidence ?? item.confidence)!)}
                  </span>
                </div>
              )}
            </div>
            <div style={{ fontSize: 14, color: "var(--text-primary)", lineHeight: 1.6 }}>
              {inv?.recommended_action || item.recommended_next_step || "No recommendation available yet."}
            </div>
            {item.runbook_url && (
              <div style={{ marginTop: "var(--space-3)", paddingTop: "var(--space-3)", borderTop: "1px solid var(--border-brain)" }}>
                <a href={item.runbook_url} target="_blank" rel="noopener noreferrer" style={{ color: "var(--accent-brain)", fontSize: 13, display: "flex", alignItems: "center", gap: "var(--space-2)" }}>
                  📖 View runbook
                </a>
              </div>
            )}
          </div>

          {/* Trigger Investigation */}
          <button onClick={triggerInvestigation} disabled={acting} style={{
            padding: "12px 16px", background: "var(--bg-surface)",
            border: "1px solid var(--border-brain)", borderRadius: "var(--radius-lg)",
            color: "var(--accent-brain)", fontSize: 13, fontWeight: 600, cursor: "pointer",
            display: "flex", alignItems: "center", justifyContent: "center", gap: "var(--space-2)",
            transition: "background var(--transition-fast)",
          }}>
            <Zap size={16} />
            {acting ? "Brain is investigating..." : "Run Brain Investigation"}
          </button>
        </div>
      </div>

      {/* Execution Timeline */}
      <section style={{ background: "var(--bg-surface)", border: "1px solid var(--border-default)", borderRadius: "var(--radius-lg)", padding: "var(--space-5)" }}>
        <h2 style={{ fontSize: 12, fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.06em", color: "var(--text-tertiary)", marginBottom: "var(--space-3)", paddingBottom: "var(--space-2)", borderBottom: "1px solid var(--border-subtle)" }}>
          Execution Timeline
        </h2>
        {events.length === 0 ? (
          <div style={{ fontSize: 13, color: "var(--text-tertiary)", padding: "var(--space-4) 0" }}>No execution events yet.</div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column" }}>
            {events.map((e, i) => (
              <div key={e.id} style={{
                display: "grid", gridTemplateColumns: "32px 80px 1fr",
                gap: "var(--space-2)", padding: "var(--space-3) 0",
                borderBottom: i < events.length - 1 ? "1px solid var(--border-subtle)" : "none",
                alignItems: "start",
              }}>
                <div style={{ display: "flex", flexDirection: "column", alignItems: "center" }}>
                  <div style={{
                    width: 10, height: 10, borderRadius: "50%",
                    background: e.event_type.includes("failed") || e.event_type.includes("rejected")
                      ? "var(--status-blocked)"
                      : e.event_type.includes("completed") || e.event_type.includes("verified")
                      ? "var(--status-done)"
                      : "var(--accent-brain)",
                    marginTop: 4,
                  }} />
                </div>
                <span style={{ fontFamily: "var(--font-mono)", fontSize: 11, color: "var(--text-tertiary)", fontVariantNumeric: "tabular-nums" }}>
                  {new Date(e.occurred_at).toLocaleTimeString()}
                </span>
                <div>
                  <div style={{ fontSize: 13, fontWeight: 500 }}>
                    {EVENT_ICONS[e.event_type] || "•"} {e.event_type.replace(/_/g, " ")}
                  </div>
                  {e.payload && Object.keys(e.payload).length > 0 && (
                    <div style={{ fontSize: 12, color: "var(--text-tertiary)", marginTop: 2 }}>
                      {Object.entries(e.payload).slice(0, 3).map(([k, v]) => (
                        <span key={k} style={{ marginRight: "var(--space-3)" }}>{k}: {String(v)}</span>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
