"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Brain, ChevronRight, Filter } from "lucide-react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import type { WorkItem } from "@pinky/contracts";
import type { PaginatedResponse } from "@pinky/contracts";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useSSE } from "@/hooks/use-sse";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";

const STATUS_BG: Record<string, string> = {
  ready: "bg-status-ready", accepted: "bg-status-accepted", in_progress: "bg-status-in-progress",
  blocked: "bg-status-blocked", waiting_for_approval: "bg-status-approval", done: "bg-status-done",
};
const STATUS_BORDER: Record<string, string> = {
  ready: "border-l-status-ready", accepted: "border-l-status-accepted", in_progress: "border-l-status-in-progress",
  blocked: "border-l-status-blocked", waiting_for_approval: "border-l-status-approval", done: "border-l-status-done",
};
const PRIORITY_BG: Record<string, string> = {
  critical: "bg-priority-critical", high: "bg-priority-high", medium: "bg-priority-medium", low: "bg-priority-low",
};

function confColor(c: number) { return c >= 0.8 ? "text-status-done" : c >= 0.5 ? "text-status-in-progress" : "text-status-blocked"; }

export default function TasksPage() {
  const [statusFilter, setStatusFilter] = useState("");
  const [priorityFilter, setPriorityFilter] = useState("");
  const [focusedIndex, setFocusedIndex] = useState(-1);
  const router = useRouter();
  const searchParams = useSearchParams();
  const cluster = searchParams.get("cluster");
  const queryClient = useQueryClient();

  const queryKey = ["work-items", cluster] as const;
  const { data, isLoading, error } = useQuery({
    queryKey,
    queryFn: () => {
      let url = `/api/v1/work-items`;
      if (cluster && cluster !== "all") url += `?cluster_id=${cluster}`;
      return api.get<PaginatedResponse<WorkItem>>(url);
    },
  });

  const items = data?.items ?? [];

  const sseHandlers = useMemo(() => ({
    update: () => queryClient.invalidateQueries({ queryKey: ["work-items"] }),
  }), [queryClient]);

  useSSE("/api/v1/streams/work-items", { onEvent: sseHandlers });

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
      <h1 className="text-xl font-semibold tracking-tight mb-5">Tasks</h1>

      <div className="grid grid-cols-4 gap-3 mb-5">
        {[
          { label: "READY", count: counts.ready, color: "bg-status-ready" },
          { label: "IN PROGRESS", count: counts.in_progress, color: "bg-status-in-progress" },
          { label: "BLOCKED", count: counts.blocked, color: "bg-status-blocked" },
          { label: "NEEDS APPROVAL", count: counts.approval, color: "bg-status-approval" },
        ].map(s => (
          <div key={s.label} className="bg-bg-surface border border-border-default rounded-lg p-3 px-4">
            <div className={`h-0.5 rounded-full mb-2 ${s.color}`} />
            <div className="tabular text-2xl font-bold">{s.count}</div>
            <div className="text-[11px] text-text-tertiary font-semibold uppercase tracking-wider">{s.label}</div>
          </div>
        ))}
      </div>

      <div className="flex gap-3 mb-4 items-center">
        <Filter size={14} className="text-text-tertiary" />
        <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)} className="bg-bg-elevated text-text-primary border border-border-default rounded-md px-2 py-1 text-xs">
          <option value="">All Statuses</option>
          <option value="ready">Ready</option>
          <option value="accepted">Accepted</option>
          <option value="in_progress">In Progress</option>
          <option value="blocked">Blocked</option>
          <option value="waiting_for_approval">Needs Approval</option>
        </select>
        <select value={priorityFilter} onChange={e => setPriorityFilter(e.target.value)} className="bg-bg-elevated text-text-primary border border-border-default rounded-md px-2 py-1 text-xs">
          <option value="">All Priorities</option>
          <option value="critical">Critical</option>
          <option value="high">High</option>
          <option value="medium">Medium</option>
          <option value="low">Low</option>
        </select>
        {(statusFilter || priorityFilter) && <Button variant="ghost" size="sm" onClick={() => { setStatusFilter(""); setPriorityFilter(""); }} className="text-xs">Clear filters</Button>}
        <span className="ml-auto text-xs text-text-tertiary">
          {filtered.length} of {items.length} tasks · <kbd className="font-mono text-[10px] px-1 py-0.5 rounded bg-bg-elevated">j</kbd>/<kbd className="font-mono text-[10px] px-1 py-0.5 rounded bg-bg-elevated">k</kbd> to navigate
        </span>
      </div>

      {isLoading && (
        <div className="flex flex-col gap-3">
          {[1, 2, 3].map(i => <div key={i} className="skeleton h-[100px] rounded-lg" />)}
        </div>
      )}

      {error && <div className="p-3 px-4 rounded-md bg-status-blocked/10 border border-status-blocked/30 text-status-blocked text-sm">Failed to load tasks: {error.message}</div>}

      {!isLoading && !error && filtered.length === 0 && (
        <div className="flex flex-col items-center py-16 px-6 text-center max-w-[360px] mx-auto">
          <div className="font-mono text-xl text-text-tertiary mb-6 select-none">( . _ . )</div>
          <div className="text-[15px] font-semibold text-text-primary mb-2">Nothing needs your attention.</div>
          <div className="text-sm text-text-secondary leading-relaxed">The Brain is watching your clusters. If something comes up, it will appear here.</div>
        </div>
      )}

      {!isLoading && filtered.length > 0 && (
        <div className="flex flex-col gap-2">
          {filtered.map((item, idx) => (
            <Link key={item.id} href={`/tasks/${item.id}`}
              className={cn(
                "block bg-bg-surface border border-border-default rounded-lg p-4 px-5 border-l-3 transition-colors no-underline",
                STATUS_BORDER[item.status] || "border-l-border-default",
                idx === focusedIndex && "ring-2 ring-border-focus",
                "hover:bg-bg-hover"
              )}
            >
              <div className="flex justify-between items-center">
                <div className="font-semibold text-sm text-text-primary">{item.title}</div>
                <div className="flex items-center gap-2">
                  <span className={cn("text-[11px] px-2 py-0.5 rounded-sm font-semibold text-white uppercase", PRIORITY_BG[item.priority])}>{item.priority}</span>
                  <span className={cn("text-[11px] px-2 py-0.5 rounded-sm font-semibold text-white uppercase", STATUS_BG[item.status])}>{item.status.replace(/_/g, " ")}</span>
                  <ChevronRight size={16} className="text-text-tertiary" />
                </div>
              </div>
              {item.why_now && <div className="text-sm text-text-secondary mt-1">{item.why_now}</div>}
              {item.recommended_next_step && (
                <div className="flex items-start gap-2 mt-2 text-sm text-accent-brain">
                  <Brain size={14} className="mt-0.5 shrink-0" />
                  <span>{item.recommended_next_step}</span>
                </div>
              )}
              <div className="flex items-center gap-3 mt-2">
                {item.confidence != null && <span className={cn("tabular text-sm font-semibold", confColor(item.confidence))}>{Math.round(item.confidence * 100)}%</span>}
                {Object.entries(item.labels).map(([k, v]) => <span key={k} className="text-[11px] px-1.5 py-0.5 bg-bg-elevated rounded-sm text-text-secondary">{k}={v}</span>)}
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
