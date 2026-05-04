"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Brain, ChevronRight, Filter } from "lucide-react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import type { WorkItem } from "@pinky/contracts";
import type { PaginatedResponse } from "@pinky/contracts";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useSSE } from "@/hooks/use-sse";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";
import { STATUS_BG, STATUS_BORDER, PRIORITY_BG, confColor } from "@/lib/status-colors";

export default function TasksPage() {
  const [statusFilter, setStatusFilter] = useState("");
  const [priorityFilter, setPriorityFilter] = useState("");
  const [focusedIndex, setFocusedIndex] = useState(-1);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
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

  const bulkMutation = useMutation({
    mutationFn: (action: string) => api.post<{ results: { id: string; status: string }[] }>("/api/v1/work-items/bulk", { ids: [...selectedIds], action }),
    onSuccess: (data, action) => {
      const ok = data.results.filter(r => r.status === "ok").length;
      toast.success(`${ok} tasks ${action === "accepted" ? "accepted" : action === "done" ? "completed" : action}`);
      setSelectedIds(new Set());
      queryClient.invalidateQueries({ queryKey: ["work-items"] });
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const toggleSelect = (id: string) => {
    setSelectedIds(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

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
    <div className="animate-fade-in">
      <h1 className="text-lg font-semibold tracking-tight mb-5 text-text-primary">Tasks</h1>

      {/* Stat strip */}
      <div className="grid grid-cols-4 gap-3 mb-6">
        {[
          { label: "READY", count: counts.ready, color: "bg-status-ready", glow: "shadow-[0_0_12px_rgba(124,172,248,0.08)]" },
          { label: "IN PROGRESS", count: counts.in_progress, color: "bg-status-in-progress", glow: "shadow-[0_0_12px_rgba(240,199,75,0.08)]" },
          { label: "BLOCKED", count: counts.blocked, color: "bg-status-blocked", glow: "shadow-[0_0_12px_rgba(240,112,112,0.08)]" },
          { label: "NEEDS APPROVAL", count: counts.approval, color: "bg-status-approval", glow: "shadow-[0_0_12px_rgba(240,152,80,0.08)]" },
        ].map(s => (
          <div key={s.label} className={cn("bg-bg-surface border border-border-default rounded-xl p-4 shadow-card", s.count > 0 && s.glow)}>
            <div className={cn("h-1 rounded-full mb-3 w-10", s.color, s.count > 0 ? "opacity-100" : "opacity-30")} />
            <div className="tabular text-[28px] font-bold font-mono leading-none">{s.count}</div>
            <div className="text-[10px] text-text-tertiary font-medium uppercase tracking-[0.1em] mt-2">{s.label}</div>
          </div>
        ))}
      </div>

      {/* Filters */}
      <div className="flex gap-3 mb-4 items-center">
        <Filter size={13} className="text-text-tertiary" />
        <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)} className="bg-bg-surface text-text-primary border border-border-default rounded-lg px-2.5 py-1.5 text-xs cursor-pointer hover:border-accent-brain/30 transition-colors focus:outline-none focus:ring-1 focus:ring-ring">
          <option value="">All Statuses</option>
          <option value="ready">Ready</option>
          <option value="accepted">Accepted</option>
          <option value="in_progress">In Progress</option>
          <option value="blocked">Blocked</option>
          <option value="waiting_for_approval">Needs Approval</option>
        </select>
        <select value={priorityFilter} onChange={e => setPriorityFilter(e.target.value)} className="bg-bg-surface text-text-primary border border-border-default rounded-lg px-2.5 py-1.5 text-xs cursor-pointer hover:border-accent-brain/30 transition-colors focus:outline-none focus:ring-1 focus:ring-ring">
          <option value="">All Priorities</option>
          <option value="critical">Critical</option>
          <option value="high">High</option>
          <option value="medium">Medium</option>
          <option value="low">Low</option>
        </select>
        {(statusFilter || priorityFilter) && <Button variant="ghost" size="sm" onClick={() => { setStatusFilter(""); setPriorityFilter(""); }} className="text-xs h-7">Clear</Button>}
        <span className="ml-auto text-xs text-text-tertiary font-mono">
          {filtered.length}/{items.length} · <kbd className="text-[10px] px-1 py-0.5 rounded border border-border-default bg-bg-surface">j</kbd>/<kbd className="text-[10px] px-1 py-0.5 rounded border border-border-default bg-bg-surface">k</kbd>
        </span>
      </div>

      {isLoading && (
        <div className="flex flex-col gap-3">
          {[1, 2, 3].map(i => <div key={i} className="skeleton h-[100px] rounded-lg" />)}
        </div>
      )}

      {error && <div className="p-3 px-4 rounded-md bg-status-blocked/10 border border-status-blocked/30 text-status-blocked text-sm">Failed to load tasks: {error.message}</div>}

      {!isLoading && !error && filtered.length === 0 && (
        <div className="flex flex-col items-center justify-center py-20 px-6 text-center">
          <div className="font-mono text-2xl text-text-tertiary mb-4 select-none">( . _ . )</div>
          <div className="text-base font-semibold text-text-primary mb-2">Nothing needs your attention.</div>
          <div className="text-sm text-text-secondary leading-relaxed max-w-[340px]">The Brain is watching your clusters. If something comes up, it will appear here.</div>
        </div>
      )}

      {/* Bulk action bar */}
      {selectedIds.size > 0 && (
        <div className="flex items-center gap-3 mb-4 p-3 px-4 bg-bg-elevated border border-border-default rounded-lg">
          <span className="text-sm font-semibold">{selectedIds.size} selected</span>
          <Button size="sm" variant="outline" className="h-7 text-xs" onClick={() => bulkMutation.mutate("accepted")} disabled={bulkMutation.isPending}>Accept All</Button>
          <Button size="sm" variant="outline" className="h-7 text-xs" onClick={() => bulkMutation.mutate("done")} disabled={bulkMutation.isPending}>Complete All</Button>
          <Button size="sm" variant="ghost" className="h-7 text-xs" onClick={() => setSelectedIds(new Set())}>Clear</Button>
        </div>
      )}

      {!isLoading && filtered.length > 0 && (
        <div className="flex flex-col gap-2">
          {filtered.map((item, idx) => (
            <div key={item.id} className="group flex items-start gap-2">
              <input
                type="checkbox"
                checked={selectedIds.has(item.id)}
                onChange={() => toggleSelect(item.id)}
                className="mt-5 ml-0.5 accent-accent-brand shrink-0 cursor-pointer opacity-40 group-hover:opacity-100 transition-opacity"
              />
            <Link href={`/tasks/${item.id}`}
              className={cn(
                "flex-1 block bg-bg-surface border border-border-default rounded-xl p-4 px-5 border-l-[3px] no-underline transition-all duration-200",
                STATUS_BORDER[item.status] || "border-l-border-default",
                idx === focusedIndex && "ring-1 ring-accent-brain/40 shadow-card-hover",
                "hover:shadow-card-hover hover:border-border-default/80"
              )}
            >
              <div className="flex justify-between items-start">
                <div className="font-medium text-[13px] text-text-primary leading-snug pr-4">{item.title}</div>
                <div className="flex items-center gap-1.5 shrink-0">
                  <span className={cn("text-[10px] px-1.5 py-0.5 rounded font-semibold uppercase tracking-wider", PRIORITY_BG[item.priority], "text-white/90")}>{item.priority}</span>
                  <span className={cn("text-[10px] px-1.5 py-0.5 rounded font-semibold uppercase tracking-wider", STATUS_BG[item.status], "text-white/90")}>{item.status.replace(/_/g, " ")}</span>
                  <ChevronRight size={14} className="text-text-tertiary ml-1 group-hover:text-text-secondary transition-colors" />
                </div>
              </div>
              {item.why_now && <div className="text-xs text-text-secondary mt-1.5 leading-relaxed">{item.why_now}</div>}
              {item.recommended_next_step && (
                <div className="flex items-start gap-2 mt-2.5 text-xs text-accent-brain/90 bg-[var(--accent-brain-bg)] rounded-lg px-3 py-2">
                  <Brain size={13} className="mt-0.5 shrink-0 text-accent-brain" />
                  <span className="leading-relaxed">{item.recommended_next_step}</span>
                </div>
              )}
              <div className="flex items-center gap-3 mt-2.5">
                {item.confidence != null && <span className={cn("tabular text-xs font-mono font-semibold", confColor(item.confidence))}>{Math.round(item.confidence * 100)}%</span>}
                {Object.entries(item.labels).map(([k, v]) => <span key={k} className="text-[10px] font-mono px-1.5 py-0.5 bg-bg-elevated/80 rounded text-text-tertiary border border-border-subtle">{k}={v}</span>)}
              </div>
            </Link>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
