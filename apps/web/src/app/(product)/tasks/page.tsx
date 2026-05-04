"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Brain, ChevronRight, Filter, Search, Check, Play, Ban, Shield, ShieldOff, ArrowUpDown } from "lucide-react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import type { WorkItem } from "@pinky/contracts";
import type { PaginatedResponse } from "@pinky/contracts";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useSSE } from "@/hooks/use-sse";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";
import { STATUS_BG, STATUS_BORDER, PRIORITY_BG, confColor } from "@/lib/status-colors";

const PRIORITY_WEIGHT: Record<string, number> = { critical: 4, high: 3, medium: 2, low: 1 };
const STATUS_WEIGHT: Record<string, number> = { ready: 3, waiting_for_approval: 2.5, blocked: 2, in_progress: 1.5, accepted: 1, done: 0 };

function urgencyScore(item: WorkItem): number {
  return (PRIORITY_WEIGHT[item.priority] ?? 1) * (STATUS_WEIGHT[item.status] ?? 1);
}

type SortMode = "urgency" | "newest" | "oldest" | "priority" | "confidence";

export default function TasksPage() {
  const [statusFilter, setStatusFilter] = useState("");
  const [priorityFilter, setPriorityFilter] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const [sortMode, setSortMode] = useState<SortMode>("urgency");
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

  // Inline action mutation
  const actionMutation = useMutation({
    mutationFn: ({ id, action }: { id: string; action: string }) =>
      api.post<WorkItem>(`/api/v1/work-items/${id}/${action}`),
    onSuccess: (_, { action }) => {
      toast.success(`Task ${action}ed`);
      queryClient.invalidateQueries({ queryKey: ["work-items"] });
    },
    onError: (e: Error) => toast.error(e.message),
  });

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

  // Filter + search + sort
  const processed = useMemo(() => {
    let result = items.filter(i => {
      if (statusFilter && i.status !== statusFilter) return false;
      if (priorityFilter && i.priority !== priorityFilter) return false;
      if (searchQuery) {
        const q = searchQuery.toLowerCase();
        const searchable = [i.title, i.why_now, i.recommended_next_step, ...Object.entries(i.labels).map(([k, v]) => `${k}=${v}`)].filter(Boolean).join(" ").toLowerCase();
        if (!searchable.includes(q)) return false;
      }
      return true;
    });

    result.sort((a, b) => {
      switch (sortMode) {
        case "urgency": return urgencyScore(b) - urgencyScore(a);
        case "priority": return (PRIORITY_WEIGHT[b.priority] ?? 0) - (PRIORITY_WEIGHT[a.priority] ?? 0);
        case "newest": return b.created_at.localeCompare(a.created_at);
        case "oldest": return a.created_at.localeCompare(b.created_at);
        case "confidence": return (b.confidence ?? 0) - (a.confidence ?? 0);
        default: return 0;
      }
    });

    return result;
  }, [items, statusFilter, priorityFilter, searchQuery, sortMode]);

  const counts = {
    ready: items.filter(i => i.status === "ready").length,
    in_progress: items.filter(i => i.status === "in_progress" || i.status === "accepted").length,
    blocked: items.filter(i => i.status === "blocked").length,
    approval: items.filter(i => i.status === "waiting_for_approval").length,
  };

  // Keyboard shortcuts
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLSelectElement || e.target instanceof HTMLTextAreaElement) return;
      if (e.key === "j") setFocusedIndex(i => Math.min(i + 1, processed.length - 1));
      if (e.key === "k") setFocusedIndex(i => Math.max(i - 1, 0));
      if (e.key === "Enter" && focusedIndex >= 0 && processed[focusedIndex]) router.push(`/tasks/${processed[focusedIndex].id}`);
      if (e.key === "x" && focusedIndex >= 0 && processed[focusedIndex]) toggleSelect(processed[focusedIndex].id);
      if (e.key === "/" ) { e.preventDefault(); document.getElementById("task-search")?.focus(); }

      // Inline actions on focused task
      if (focusedIndex >= 0 && processed[focusedIndex]) {
        const task = processed[focusedIndex];
        if (e.key === "a" && task.status === "ready") actionMutation.mutate({ id: task.id, action: "accept" });
        if (e.key === "s" && (task.status === "accepted" || task.status === "blocked")) actionMutation.mutate({ id: task.id, action: "start" });
        if (e.key === "c" && task.status === "in_progress") actionMutation.mutate({ id: task.id, action: "complete" });
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [processed, focusedIndex, router, actionMutation]);

  return (
    <div className="animate-fade-in">
      <h1 className="text-lg font-semibold tracking-tight mb-5 text-text-primary">Tasks</h1>

      {/* Stat strip */}
      <div className="grid grid-cols-4 gap-4 mb-8">
        {[
          { label: "READY", count: counts.ready, color: "bg-status-ready", glow: "shadow-[0_0_12px_rgba(111,168,247,0.1)]" },
          { label: "IN PROGRESS", count: counts.in_progress, color: "bg-status-in-progress", glow: "shadow-[0_0_12px_rgba(232,190,60,0.1)]" },
          { label: "BLOCKED", count: counts.blocked, color: "bg-status-blocked", glow: "shadow-[0_0_12px_rgba(239,107,107,0.1)]" },
          { label: "NEEDS APPROVAL", count: counts.approval, color: "bg-status-approval", glow: "shadow-[0_0_12px_rgba(232,144,64,0.1)]" },
        ].map(s => (
          <div key={s.label} className={cn("bg-bg-surface border border-border-default rounded-xl p-4 shadow-card", s.count > 0 && s.glow)}>
            <div className={cn("h-1 rounded-full mb-3 w-10", s.color, s.count > 0 ? "opacity-100" : "opacity-30")} />
            <div className="tabular text-[28px] font-bold font-mono leading-none">{s.count}</div>
            <div className="text-xs text-text-tertiary font-medium uppercase tracking-[0.1em] mt-2">{s.label}</div>
          </div>
        ))}
      </div>

      {/* Search + Filters + Sort */}
      <div className="flex gap-3 mb-6 items-center">
        <div className="relative flex-1 max-w-[280px]">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-text-tertiary" />
          <Input
            id="task-search"
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            placeholder="Search tasks..."
            className="pl-9 h-8 text-xs bg-bg-surface"
          />
        </div>
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
        <div className="flex items-center gap-1.5 text-xs text-text-tertiary">
          <ArrowUpDown size={12} />
          <select value={sortMode} onChange={e => setSortMode(e.target.value as SortMode)} className="bg-bg-surface text-text-primary border border-border-default rounded-lg px-2 py-1.5 text-xs cursor-pointer focus:outline-none focus:ring-1 focus:ring-ring">
            <option value="urgency">Urgency</option>
            <option value="priority">Priority</option>
            <option value="newest">Newest</option>
            <option value="oldest">Oldest</option>
            <option value="confidence">Confidence</option>
          </select>
        </div>
        {(statusFilter || priorityFilter || searchQuery) && <Button variant="ghost" size="sm" onClick={() => { setStatusFilter(""); setPriorityFilter(""); setSearchQuery(""); }} className="text-xs h-7">Clear</Button>}
        <span className="ml-auto text-xs text-text-tertiary font-mono">
          {processed.length}/{items.length}
        </span>
      </div>

      {isLoading && (
        <div className="flex flex-col gap-3">
          {[1, 2, 3].map(i => <div key={i} className="skeleton h-[100px] rounded-lg" />)}
        </div>
      )}

      {error && <div className="p-3 px-4 rounded-lg bg-status-blocked/10 border border-status-blocked/30 text-status-blocked text-sm">Failed to load tasks: {error.message}</div>}

      {!isLoading && !error && processed.length === 0 && (
        <div className="flex flex-col items-center justify-center py-20 px-6 text-center">
          <div className="font-mono text-2xl text-text-tertiary mb-4 select-none">( . _ . )</div>
          <div className="text-base font-semibold text-text-primary mb-2">
            {searchQuery ? "No tasks match your search." : "Nothing needs your attention."}
          </div>
          <div className="text-sm text-text-secondary leading-relaxed max-w-[360px]">
            {searchQuery
              ? "Try different search terms or clear your filters."
              : "The Brain is watching your clusters. Tasks appear here when issues are detected."}
          </div>
          {!searchQuery && items.length === 0 && (
            <Link href="/settings" className="text-accent-brand text-sm mt-4 font-medium">
              Configure clusters →
            </Link>
          )}
        </div>
      )}

      {/* Bulk action bar */}
      {selectedIds.size > 0 && (
        <div className="flex items-center gap-3 mb-4 p-3 px-4 bg-bg-elevated border border-border-default rounded-xl">
          <span className="text-sm font-semibold">{selectedIds.size} selected</span>
          <Button size="sm" variant="outline" className="h-7 text-xs" onClick={() => bulkMutation.mutate("accepted")} disabled={bulkMutation.isPending}>Accept All</Button>
          <Button size="sm" variant="outline" className="h-7 text-xs" onClick={() => bulkMutation.mutate("done")} disabled={bulkMutation.isPending}>Complete All</Button>
          <Button size="sm" variant="ghost" className="h-7 text-xs" onClick={() => setSelectedIds(new Set())}>Clear</Button>
        </div>
      )}

      {!isLoading && processed.length > 0 && (
        <div className="flex flex-col gap-2.5">
          {processed.map((item, idx) => (
            <div key={item.id} className="group flex items-start gap-2">
              <input
                type="checkbox"
                checked={selectedIds.has(item.id)}
                onChange={() => toggleSelect(item.id)}
                className="mt-5 ml-0.5 accent-accent-brand shrink-0 cursor-pointer opacity-0 group-hover:opacity-100 transition-opacity"
              />
              <div
                className={cn(
                  "flex-1 bg-bg-surface border border-border-default rounded-xl p-4 px-5 border-l-[3px] transition-all duration-200",
                  STATUS_BORDER[item.status] || "border-l-border-default",
                  idx === focusedIndex && "ring-1 ring-accent-brain/40 shadow-card-hover",
                  "hover:shadow-card-hover"
                )}
              >
                <div className="flex justify-between items-start gap-4">
                  {/* Left: title + details */}
                  <Link href={`/tasks/${item.id}`} className="flex-1 no-underline min-w-0">
                    <div className="font-medium text-[13px] text-text-primary leading-snug">{item.title}</div>
                    {item.why_now && <div className="text-xs text-text-secondary mt-1.5 leading-relaxed truncate">{item.why_now}</div>}
                  </Link>

                  {/* Right: badges + inline actions */}
                  <div className="flex items-center gap-2 shrink-0">
                    <span className={cn("text-xs px-1.5 py-0.5 rounded font-semibold uppercase tracking-wider text-white/90", PRIORITY_BG[item.priority])}>{item.priority}</span>
                    <span className={cn("text-xs px-1.5 py-0.5 rounded font-semibold uppercase tracking-wider text-white/90", STATUS_BG[item.status])}>{item.status.replace(/_/g, " ")}</span>

                    {/* Inline action buttons */}
                    {item.status === "ready" && (
                      <Button size="xs" variant="outline" className="opacity-0 group-hover:opacity-100 transition-opacity" onClick={() => actionMutation.mutate({ id: item.id, action: "accept" })} disabled={actionMutation.isPending}>
                        <Check size={12} /> Accept
                      </Button>
                    )}
                    {(item.status === "accepted" || item.status === "blocked") && (
                      <Button size="xs" variant="outline" className="opacity-0 group-hover:opacity-100 transition-opacity" onClick={() => actionMutation.mutate({ id: item.id, action: "start" })} disabled={actionMutation.isPending}>
                        <Play size={12} /> Start
                      </Button>
                    )}
                    {item.status === "in_progress" && (
                      <Button size="xs" variant="outline" className="opacity-0 group-hover:opacity-100 transition-opacity" onClick={() => actionMutation.mutate({ id: item.id, action: "complete" })} disabled={actionMutation.isPending}>
                        <Check size={12} /> Complete
                      </Button>
                    )}

                    <Link href={`/tasks/${item.id}`} className="text-text-tertiary hover:text-text-secondary no-underline">
                      <ChevronRight size={14} />
                    </Link>
                  </div>
                </div>

                {/* Brain recommendation */}
                {item.recommended_next_step && (
                  <div className="flex items-start gap-2 mt-2.5 text-xs text-accent-brain/90 bg-[var(--accent-brain-bg)] rounded-lg px-3 py-2">
                    <Brain size={13} className="mt-0.5 shrink-0 text-accent-brain" />
                    <span className="leading-relaxed">{item.recommended_next_step}</span>
                  </div>
                )}

                {/* Meta row */}
                <div className="flex items-center gap-3 mt-2.5">
                  {item.confidence != null && <span className={cn("tabular text-xs font-mono font-semibold", confColor(item.confidence))}>{Math.round(item.confidence * 100)}%</span>}
                  {Object.entries(item.labels).map(([k, v]) => <span key={k} className="text-xs font-mono px-1.5 py-0.5 bg-bg-elevated/80 rounded text-text-tertiary border border-border-subtle">{k}={v}</span>)}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
