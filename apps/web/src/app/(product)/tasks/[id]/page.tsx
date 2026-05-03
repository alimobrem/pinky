"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { ArrowLeft, Brain, CheckCircle, Play, ChevronDown, ChevronRight, Zap } from "lucide-react";
import { useToast } from "@/components/toast";
import css from "./page.module.css";

const API = "";

interface WorkItem {
  id: string; title: string; why_now: string | null; recommended_next_step: string | null;
  status: string; priority: string; confidence: number | null; owner_id: string | null;
  labels: Record<string, string>; cluster_id: string; runbook_url: string | null; created_at: string;
}

interface Investigation {
  has_investigation: boolean; summary?: string; root_cause?: string; recommended_action?: string;
  confidence?: number; tool_calls?: string[]; created_at?: string;
}

interface TimelineEvent {
  id: string; execution_id: string; event_type: string; sequence: number;
  payload: Record<string, unknown>; occurred_at: string;
}

const STATUS_COLORS: Record<string, string> = {
  ready: "var(--status-ready)", accepted: "var(--status-accepted)", in_progress: "var(--status-in-progress)",
  blocked: "var(--status-blocked)", waiting_for_approval: "var(--status-approval)", done: "var(--status-done)",
};
const PRIORITY_COLORS: Record<string, string> = {
  critical: "var(--priority-critical)", high: "var(--priority-high)", medium: "var(--priority-medium)", low: "var(--priority-low)",
};

function confColor(c: number) { return c >= 0.8 ? "var(--status-done)" : c >= 0.5 ? "var(--status-in-progress)" : "var(--status-blocked)"; }
function confLabel(c: number) { return c >= 0.8 ? "High confidence" : c >= 0.5 ? "Moderate confidence" : "Low confidence"; }

const VALID_ACTIONS: Record<string, string[]> = { ready: ["accept"], accepted: ["start"], in_progress: ["complete"], blocked: ["start"] };
const EVENT_ICONS: Record<string, string> = { started: "🚀", completed: "✅", failed: "❌", investigation_completed: "🔍", verified: "✓" };

export default function TaskDetailPage() {
  const params = useParams();
  const router = useRouter();
  const taskId = params.id as string;
  const { toast } = useToast();

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
    ]).then(([wi, inv, evts]) => { setItem(wi); setInvestigation(inv); setEvents(evts.items || []); setLoading(false); });
  }, [taskId]);

  const doAction = async (action: string) => {
    setActing(true);
    const r = await fetch(`${API}/api/v1/work-items/${taskId}/${action}`, { method: "POST" });
    if (r.ok) { setItem(await r.json()); toast(`Task ${action}ed successfully`, "success"); }
    else { const err = await r.json().catch(() => ({})); toast(err.detail || `Failed to ${action}`, "error"); }
    setActing(false);
  };

  const triggerInvestigation = async () => {
    setActing(true); toast("Brain investigation started...", "info");
    await fetch(`${API}/api/v1/executions?work_item_id=${taskId}&execution_type=investigation`, { method: "POST" });
    setTimeout(async () => {
      const [inv, evts] = await Promise.all([
        fetch(`${API}/api/v1/work-items/${taskId}/investigation`).then(r => r.json()),
        fetch(`${API}/api/v1/work-items/${taskId}/events`).then(r => r.json()),
      ]);
      setInvestigation(inv); setEvents(evts.items || []); setActing(false);
    }, 2000);
  };

  if (loading) return (
    <div className={css.column}>
      {[1, 2, 3].map(i => <div key={i} className="skeleton" style={{ height: i === 1 ? 60 : 180, borderRadius: "var(--radius-lg)" }} />)}
    </div>
  );

  if (!item) return <div className={css.emptyInvestigation}>Task not found.</div>;

  const actions = VALID_ACTIONS[item.status] || [];
  const inv = investigation?.has_investigation ? investigation : null;

  return (
    <div>
      <div className={css.actionBar}>
        <button onClick={() => router.push("/tasks")} className={css.backButton}><ArrowLeft size={16} /> Back to Tasks</button>
        <div className={css.actions}>
          {actions.includes("accept") && <button onClick={() => doAction("accept")} disabled={acting} className={css.btnPrimary}>Accept</button>}
          {actions.includes("start") && <button onClick={() => doAction("start")} disabled={acting} className={css.btnPrimary}><Play size={14} />Start</button>}
          {actions.includes("complete") && <button onClick={() => doAction("complete")} disabled={acting} className={css.btnSecondary}><CheckCircle size={14} />Complete</button>}
        </div>
      </div>

      <div className={css.header}>
        <h1 className={css.title}>{item.title}</h1>
        <div className={css.meta}>
          <span className={css.badge} style={{ background: PRIORITY_COLORS[item.priority] }}>{item.priority}</span>
          <span className={css.badge} style={{ background: STATUS_COLORS[item.status] }}>{item.status.replace(/_/g, " ")}</span>
          {Object.entries(item.labels).map(([k, v]) => <span key={k} className={css.label}>{k}={v}</span>)}
        </div>
      </div>

      <div className={css.twoColumn}>
        <div className={css.column}>
          <section className={css.section}>
            <h2 className={css.sectionHeader}>Summary</h2>
            {item.why_now && <div style={{ marginBottom: "var(--space-4)" }}><div className={css.sectionLabel}>Why now</div><div className={css.sectionBody}>{item.why_now}</div></div>}
            <div className={css.sectionLabel}>Created {new Date(item.created_at).toLocaleString()}</div>
          </section>

          {inv ? (
            <section className={css.section}>
              <h2 className={css.sectionHeader}><Brain size={14} style={{ color: "var(--accent-brain)" }} /> Investigation Results</h2>
              {inv.summary && <div className={css.reasoning}>{inv.summary}</div>}
              {inv.root_cause && inv.root_cause !== inv.summary && (
                <div>
                  <button onClick={() => setShowReasoning(!showReasoning)} className={css.toggleBtn}>
                    {showReasoning ? <ChevronDown size={14} /> : <ChevronRight size={14} />} View full analysis
                  </button>
                  {showReasoning && <div className={css.reasoningExpanded}>{inv.root_cause}</div>}
                </div>
              )}
              <div className={css.sectionLabel} style={{ marginTop: "var(--space-3)" }}>Investigated {inv.created_at ? new Date(inv.created_at).toLocaleString() : "recently"}</div>
            </section>
          ) : (
            <section className={`${css.section} ${css.emptyInvestigation}`}>
              <Brain size={24} style={{ color: "var(--text-tertiary)", marginBottom: "var(--space-3)" }} />
              <p style={{ color: "var(--text-secondary)", marginBottom: "var(--space-2)" }}>No investigation data yet.</p>
              <p style={{ fontSize: 13, color: "var(--text-tertiary)" }}>Trigger an investigation to have The Brain analyze this issue.</p>
            </section>
          )}
        </div>

        <div className={css.column}>
          <div className={css.brainBlock}>
            <div className={css.brainHeader}>
              <div className={css.brainLabel}><Brain size={16} /> The Brain recommends</div>
              {(inv?.confidence ?? item.confidence) != null && (
                <div style={{ textAlign: "right" }}>
                  <div className={css.confidenceValue} style={{ color: confColor((inv?.confidence ?? item.confidence)!) }}>{Math.round((inv?.confidence ?? item.confidence)! * 100)}%</div>
                  <div className={css.confidenceLabel}>{confLabel((inv?.confidence ?? item.confidence)!)}</div>
                </div>
              )}
            </div>
            <div className={css.brainBody}>{inv?.recommended_action || item.recommended_next_step || "No recommendation available yet."}</div>
            {item.runbook_url && <div className={css.runbookLink}><a href={item.runbook_url} target="_blank" rel="noopener noreferrer">📖 View runbook</a></div>}
          </div>
          <button onClick={triggerInvestigation} disabled={acting} className={css.investigateBtn}>
            <Zap size={16} /> {acting ? "Brain is investigating..." : "Run Brain Investigation"}
          </button>
        </div>
      </div>

      <section className={css.section}>
        <h2 className={css.sectionHeader}>Execution Timeline</h2>
        {events.length === 0 ? (
          <p style={{ fontSize: 13, color: "var(--text-tertiary)", padding: "var(--space-4) 0" }}>No execution events yet.</p>
        ) : (
          <div>{events.map(e => (
            <div key={e.id} className={css.timelineEntry}>
              <div style={{ display: "flex", justifyContent: "center" }}>
                <div className={css.timelineDot} style={{
                  background: e.event_type.includes("failed") ? "var(--status-blocked)" :
                    e.event_type.includes("completed") || e.event_type.includes("verified") ? "var(--status-done)" : "var(--accent-brain)",
                }} />
              </div>
              <span className={css.timelineTime}>{new Date(e.occurred_at).toLocaleTimeString()}</span>
              <div>
                <div className={css.timelineEvent}>{EVENT_ICONS[e.event_type] || "•"} {e.event_type.replace(/_/g, " ")}</div>
                {e.payload && Object.keys(e.payload).length > 0 && (
                  <div className={css.timelinePayload}>{Object.entries(e.payload).slice(0, 3).map(([k, v]) => <span key={k}>{k}: {String(v)}</span>)}</div>
                )}
              </div>
            </div>
          ))}</div>
        )}
      </section>
    </div>
  );
}
