"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Brain, ChevronRight, Filter } from "lucide-react";
import css from "./page.module.css";

const API = "";

interface WorkItem {
  id: string; title: string; why_now: string | null; recommended_next_step: string | null;
  status: string; priority: string; confidence: number | null; owner_id: string | null;
  labels: Record<string, string>; cluster_id: string; runbook_url: string | null;
}

const STATUS_COLORS: Record<string, string> = {
  ready: "var(--status-ready)", accepted: "var(--status-accepted)", in_progress: "var(--status-in-progress)",
  blocked: "var(--status-blocked)", waiting_for_approval: "var(--status-approval)", done: "var(--status-done)",
};
const PRIORITY_COLORS: Record<string, string> = {
  critical: "var(--priority-critical)", high: "var(--priority-high)", medium: "var(--priority-medium)", low: "var(--priority-low)",
};

function confColor(c: number) { return c >= 0.8 ? "var(--status-done)" : c >= 0.5 ? "var(--status-in-progress)" : "var(--status-blocked)"; }

export default function TasksPage() {
  const [items, setItems] = useState<WorkItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState("");
  const [priorityFilter, setPriorityFilter] = useState("");
  const [focusedIndex, setFocusedIndex] = useState(-1);
  const router = useRouter();
  const searchParams = useSearchParams();
  const cluster = searchParams.get("cluster");

  const fetchItems = () => {
    let url = `${API}/api/v1/work-items`;
    if (cluster && cluster !== "all") url += `?cluster_id=${cluster}`;
    fetch(url)
      .then(r => { if (!r.ok) throw new Error(`${r.status}`); return r.json(); })
      .then(data => { setItems(data.items || []); setLoading(false); })
      .catch(e => { setError(e.message); setLoading(false); });
  };

  useEffect(() => {
    fetchItems();
    const es = new EventSource(`${API}/api/v1/streams/work-items`);
    es.addEventListener("update", () => fetchItems());
    es.addEventListener("heartbeat", () => {});
    es.onerror = () => {};
    return () => es.close();
  }, [cluster]);

  const filtered = items.filter(i => {
    if (statusFilter && i.status !== statusFilter) return false;
    if (priorityFilter && i.priority !== priorityFilter) return false;
    return true;
  });

  const counts = {
    ready: items.filter(i => i.status === "ready").length,
    in_progress: items.filter(i => i.status === "in_progress" || i.status === "accepted").length,
    blocked: items.filter(i => i.status === "blocked").length,
    approval: items.filter(i => i.status === "waiting_for_approval").length,
  };

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLSelectElement) return;
      if (e.key === "j") setFocusedIndex(i => Math.min(i + 1, filtered.length - 1));
      if (e.key === "k") setFocusedIndex(i => Math.max(i - 1, 0));
      if (e.key === "Enter" && focusedIndex >= 0 && filtered[focusedIndex]) router.push(`/tasks/${filtered[focusedIndex].id}`);
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [filtered, focusedIndex, router]);

  return (
    <div>
      <h1 className={css.heading}>Tasks</h1>

      <div className={css.statStrip}>
        {[
          { label: "READY", count: counts.ready, color: "var(--status-ready)" },
          { label: "IN PROGRESS", count: counts.in_progress, color: "var(--status-in-progress)" },
          { label: "BLOCKED", count: counts.blocked, color: "var(--status-blocked)" },
          { label: "NEEDS APPROVAL", count: counts.approval, color: "var(--status-approval)" },
        ].map(s => (
          <div key={s.label} className={css.statCard}>
            <div className={css.statBar} style={{ background: s.color }} />
            <div className={`${css.statCount} tabular`}>{s.count}</div>
            <div className={css.statLabel}>{s.label}</div>
          </div>
        ))}
      </div>

      <div className={css.filterBar}>
        <Filter size={14} style={{ color: "var(--text-tertiary)" }} />
        <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)} className={css.filterSelect}>
          <option value="">All Statuses</option>
          <option value="ready">Ready</option>
          <option value="accepted">Accepted</option>
          <option value="in_progress">In Progress</option>
          <option value="blocked">Blocked</option>
          <option value="waiting_for_approval">Needs Approval</option>
        </select>
        <select value={priorityFilter} onChange={e => setPriorityFilter(e.target.value)} className={css.filterSelect}>
          <option value="">All Priorities</option>
          <option value="critical">Critical</option>
          <option value="high">High</option>
          <option value="medium">Medium</option>
          <option value="low">Low</option>
        </select>
        {(statusFilter || priorityFilter) && <button onClick={() => { setStatusFilter(""); setPriorityFilter(""); }} className={css.clearBtn}>Clear filters</button>}
        <span className={css.filterInfo}>
          {filtered.length} of {items.length} tasks · <kbd className={css.filterKbd}>j</kbd>/<kbd className={css.filterKbd}>k</kbd> to navigate
        </span>
      </div>

      {loading && (
        <div className={css.skeletons}>
          {[1, 2, 3].map(i => <div key={i} className="skeleton" style={{ height: 100, borderRadius: "var(--radius-lg)" }} />)}
        </div>
      )}

      {error && <div className={css.error}>Failed to load tasks: {error}</div>}

      {!loading && !error && filtered.length === 0 && (
        <div className={css.empty}>
          <div className={css.emptyFace}>( . _ . )</div>
          <div className={css.emptyTitle}>Nothing needs your attention.</div>
          <div className={css.emptyDesc}>The Brain is watching your clusters. If something comes up, it will appear here.</div>
        </div>
      )}

      {!loading && filtered.length > 0 && (
        <div className={css.list}>
          {filtered.map((item, idx) => (
            <Link key={item.id} href={`/tasks/${item.id}`} className={idx === focusedIndex ? css.cardFocused : css.card} style={{ borderLeft: `3px solid ${STATUS_COLORS[item.status] || "var(--border-default)"}` }}>
              <div className={css.cardTop}>
                <div className={css.cardTitle}>{item.title}</div>
                <div className={css.cardBadges}>
                  <span className={css.badge} style={{ background: PRIORITY_COLORS[item.priority] }}>{item.priority}</span>
                  <span className={css.badge} style={{ background: STATUS_COLORS[item.status] }}>{item.status.replace(/_/g, " ")}</span>
                  <ChevronRight size={16} style={{ color: "var(--text-tertiary)" }} />
                </div>
              </div>
              {item.why_now && <div className={css.whyNow}>{item.why_now}</div>}
              {item.recommended_next_step && (
                <div className={css.brainRec}>
                  <Brain size={14} style={{ marginTop: 2, flexShrink: 0 }} />
                  <span>{item.recommended_next_step}</span>
                </div>
              )}
              <div className={css.cardMeta}>
                {item.confidence != null && <span className={css.confidenceValue} style={{ color: confColor(item.confidence) }}>{Math.round(item.confidence * 100)}%</span>}
                {Object.entries(item.labels).map(([k, v]) => <span key={k} className={css.label}>{k}={v}</span>)}
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
