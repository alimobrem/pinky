"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import {
  ArrowUpDown,
  Ban,
  Brain,
  Check,
  CheckSquare,
  ChevronRight,
  Clock,
  ExternalLink,
  Link2,
  Play,
  Search,
  Shield,
} from "lucide-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import type { ClusterRegistryEntry, PaginatedResponse, WorkItem } from "@pinky/contracts";
import { EmptyState } from "@/components/empty-state";
import { PageHeader } from "@/components/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useSSE } from "@/hooks/use-sse";
import { api } from "@/lib/api";
import { relativeTime } from "@/lib/format-date";
import { cn } from "@/lib/utils";
import { PRIORITY_BG, STATUS_BG, confColor } from "@/lib/status-colors";

const PRIORITY_WEIGHT: Record<string, number> = { critical: 4, high: 3, medium: 2, low: 1 };
const STATUS_WEIGHT: Record<string, number> = {
  ready: 3,
  waiting_for_approval: 2.5,
  blocked: 2,
  in_progress: 1.5,
  accepted: 1,
  done: 0,
};
const EMPTY_ITEMS: WorkItem[] = [];
const QUEUES = [
  {
    id: "all",
    label: "All tasks",
    description: "Everything The Brain surfaced for review.",
    status: "",
  },
  {
    id: "ready",
    label: "Ready to triage",
    description: "Fresh work that needs a human read.",
    status: "ready",
  },
  {
    id: "active",
    label: "In progress",
    description: "Accepted or actively being worked.",
    status: "accepted,in_progress",
  },
  {
    id: "blocked",
    label: "Blocked",
    description: "Needs an unblock before it can move.",
    status: "blocked",
  },
  {
    id: "approval",
    label: "Needs approval",
    description: "Waiting on a human decision to continue.",
    status: "waiting_for_approval",
  },
] as const;

function urgencyScore(item: WorkItem): number {
  return (PRIORITY_WEIGHT[item.priority] ?? 1) * (STATUS_WEIGHT[item.status] ?? 1);
}

function countForStatus(items: WorkItem[], status: string): number {
  if (!status) return items.length;
  const statuses = status.split(",");
  return items.filter((item) => statuses.includes(item.status)).length;
}

function getQueueId(statusFilter: string): string {
  const match = QUEUES.find((queue) => queue.status === statusFilter);
  return match?.id ?? "all";
}

type SortMode = "urgency" | "newest" | "oldest" | "priority" | "confidence";

function getTaskExcerpt(item: WorkItem): string {
  const source = item.why_now || item.recommended_next_step || "Awaiting a fuller investigation summary.";
  if (source.length <= 180) return source;
  return `${source.slice(0, 177).trimEnd()}...`;
}

function getVisibleLabels(item: WorkItem): Array<[string, string]> {
  return Object.entries(item.labels).slice(0, 2);
}

interface TaskPreviewPanelProps {
  task: WorkItem;
  clusterName: string;
  acting: boolean;
  onAccept: () => void;
  onStart: () => void;
  onComplete: () => void;
  onOpen: () => void;
}

function TaskPreviewPanel({
  task,
  clusterName,
  acting,
  onAccept,
  onStart,
  onComplete,
  onOpen,
}: TaskPreviewPanelProps) {
  return (
    <section className="rounded-2xl border border-accent-brain/25 bg-[linear-gradient(135deg,rgba(15,14,23,0.98),rgba(28,24,44,0.96))] p-5 shadow-[0_0_30px_rgba(167,139,250,0.06)]">
      <div className="mb-3 flex items-center justify-between gap-3">
        <div className="text-xs font-semibold uppercase tracking-[0.16em] text-accent-brain">
          Selected task
        </div>
        <Badge variant="outline" className="rounded-full border-border-subtle bg-bg-elevated text-text-secondary">
          {clusterName}
        </Badge>
      </div>

      <div className="space-y-4">
        <div className="space-y-2">
          <h2 className="text-xl font-semibold leading-tight text-text-primary">{task.title}</h2>
          <p className="text-sm leading-relaxed text-text-secondary">{task.why_now || "No short triage summary is available yet."}</p>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div className="rounded-xl border border-border-subtle bg-bg-elevated/80 px-3 py-3">
            <div className="text-xs font-semibold uppercase tracking-[0.16em] text-text-tertiary">Priority</div>
            <div className="mt-2 text-sm font-semibold text-text-primary">{task.priority}</div>
          </div>
          <div className="rounded-xl border border-border-subtle bg-bg-elevated/80 px-3 py-3">
            <div className="text-xs font-semibold uppercase tracking-[0.16em] text-text-tertiary">Status</div>
            <div className="mt-2 text-sm font-semibold text-text-primary">{task.status.replace(/_/g, " ")}</div>
          </div>
          <div className="rounded-xl border border-border-subtle bg-bg-elevated/80 px-3 py-3">
            <div className="text-xs font-semibold uppercase tracking-[0.16em] text-text-tertiary">Confidence</div>
            <div className={cn("mt-2 text-sm font-semibold", task.confidence != null ? confColor(task.confidence) : "text-text-primary")}>
              {task.confidence != null ? `${Math.round(task.confidence * 100)}%` : "Unknown"}
            </div>
          </div>
          <div className="rounded-xl border border-border-subtle bg-bg-elevated/80 px-3 py-3">
            <div className="text-xs font-semibold uppercase tracking-[0.16em] text-text-tertiary">Created</div>
            <div className="mt-2 text-sm font-semibold text-text-primary">
              {task.created_at ? relativeTime(task.created_at) : "Recent"}
            </div>
          </div>
        </div>

        <div className="rounded-xl border border-border-subtle bg-bg-elevated/50 px-4 py-4">
          <div className="mb-2 flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.16em] text-accent-brain">
            <Brain size={12} />
            Next best move
          </div>
          <p className="text-sm leading-relaxed text-text-secondary">
            {task.recommended_next_step || "The Brain has not proposed a next step for this task yet."}
          </p>
        </div>

        {task.blocked_reason ? (
          <div className="rounded-xl border border-status-blocked/25 bg-status-blocked/10 px-4 py-4 text-sm text-status-blocked">
            <div className="mb-2 flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.16em]">
              <Ban size={12} />
              Current blocker
            </div>
            {task.blocked_reason}
          </div>
        ) : null}

        <div className="flex flex-wrap gap-2">
          {task.status === "ready" ? (
            <Button size="sm" onClick={onAccept} disabled={acting}>
              <Check size={14} />
              Accept
            </Button>
          ) : null}
          {(task.status === "accepted" || task.status === "blocked") ? (
            <Button size="sm" onClick={onStart} disabled={acting}>
              <Play size={14} />
              Start
            </Button>
          ) : null}
          {task.status === "in_progress" ? (
            <Button size="sm" variant="secondary" onClick={onComplete} disabled={acting}>
              <Check size={14} />
              Complete
            </Button>
          ) : null}
          {task.status === "waiting_for_approval" ? (
            <Button size="sm" variant="outline" onClick={onOpen}>
              <Shield size={14} />
              Review approvals
            </Button>
          ) : null}
          <Button size="sm" variant="ghost" onClick={onOpen}>
            Open task
            <ChevronRight size={14} />
          </Button>
        </div>
      </div>
    </section>
  );
}

export default function TasksPage() {
  const [statusFilter, setStatusFilter] = useState("");
  const [priorityFilter, setPriorityFilter] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const [sortMode, setSortMode] = useState<SortMode>("urgency");
  const [activeTaskId, setActiveTaskId] = useState<string | null>(null);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const lastKeyboardNavRef = useRef(0);
  const router = useRouter();
  const searchParams = useSearchParams();
  const cluster = searchParams.get("cluster");
  const queryClient = useQueryClient();

  const { data, isLoading, error } = useQuery({
    queryKey: ["work-items", cluster, statusFilter, priorityFilter],
    queryFn: () => {
      const params = new URLSearchParams();
      if (cluster && cluster !== "all") params.set("cluster_id", cluster);
      if (statusFilter) params.set("status", statusFilter);
      if (priorityFilter) params.set("priority", priorityFilter);
      params.set("limit", "100");
      return api.get<PaginatedResponse<WorkItem>>(`/api/v1/work-items?${params.toString()}`);
    },
  });
  const { data: allTasksData } = useQuery({
    queryKey: ["work-items-overview", cluster],
    queryFn: () => {
      const params = new URLSearchParams();
      if (cluster && cluster !== "all") params.set("cluster_id", cluster);
      params.set("limit", "100");
      return api.get<PaginatedResponse<WorkItem>>(`/api/v1/work-items?${params.toString()}`);
    },
  });
  const { data: clustersData } = useQuery({
    queryKey: ["clusters"],
    queryFn: () => api.get<PaginatedResponse<ClusterRegistryEntry>>("/api/v1/clusters"),
    staleTime: 30_000,
  });

  const items = data?.items ?? EMPTY_ITEMS;
  const allTasks = allTasksData?.items ?? EMPTY_ITEMS;
  const activeQueue = getQueueId(statusFilter);
  const clusterMap = useMemo(
    () => new Map((clustersData?.items ?? []).map((entry) => [entry.id, entry.display_name])),
    [clustersData],
  );

  const sseHandlers = useMemo(
    () => ({
      update: () => queryClient.invalidateQueries({ queryKey: ["work-items"] }),
    }),
    [queryClient],
  );

  useSSE("/api/v1/streams/work-items", { onEvent: sseHandlers });

  const actionMutation = useMutation({
    mutationFn: ({ id, action }: { id: string; action: string }) =>
      api.post<WorkItem>(`/api/v1/work-items/${id}/${action}`),
    onSuccess: (_, { action }) => {
      toast.success(`Task ${action}ed`);
      queryClient.invalidateQueries({ queryKey: ["work-items"] });
      queryClient.invalidateQueries({ queryKey: ["work-items-overview"] });
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const bulkMutation = useMutation({
    mutationFn: (action: string) =>
      api.post<{ results: { id: string; status: string }[] }>("/api/v1/work-items/bulk", {
        ids: [...selectedIds],
        action,
      }),
    onSuccess: (result, action) => {
      const ok = result.results.filter((entry) => entry.status === "ok").length;
      toast.success(
        `${ok} tasks ${action === "accepted" ? "accepted" : action === "done" ? "completed" : action}`,
      );
      setSelectedIds(new Set());
      queryClient.invalidateQueries({ queryKey: ["work-items"] });
      queryClient.invalidateQueries({ queryKey: ["work-items-overview"] });
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const handleMouseEnter = useCallback((id: string) => {
    if (Date.now() - lastKeyboardNavRef.current > 800) {
      setActiveTaskId(id);
    }
  }, []);

  const toggleSelect = (id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const processed = useMemo(() => {
    const result = items.filter((item) => {
      if (searchQuery) {
        const q = searchQuery.toLowerCase();
        const searchable = [
          item.title,
          item.why_now,
          item.recommended_next_step,
          item.blocked_reason,
          clusterMap.get(item.cluster_id),
          ...Object.entries(item.labels).map(([k, v]) => `${k}=${v}`),
        ]
          .filter(Boolean)
          .join(" ")
          .toLowerCase();
        if (!searchable.includes(q)) return false;
      }
      return true;
    });

    result.sort((a, b) => {
      switch (sortMode) {
        case "urgency":
          return urgencyScore(b) - urgencyScore(a);
        case "priority":
          return (PRIORITY_WEIGHT[b.priority] ?? 0) - (PRIORITY_WEIGHT[a.priority] ?? 0);
        case "newest":
          return b.created_at.localeCompare(a.created_at);
        case "oldest":
          return a.created_at.localeCompare(b.created_at);
        case "confidence":
          return (b.confidence ?? 0) - (a.confidence ?? 0);
        default:
          return 0;
      }
    });

    return result;
  }, [items, searchQuery, sortMode, clusterMap]);

  const queueCounts = useMemo(
    () => Object.fromEntries(QUEUES.map((queue) => [queue.id, countForStatus(allTasks, queue.status)])),
    [allTasks],
  );

  useEffect(() => {
    if (processed.length === 0) {
      setActiveTaskId(null);
      return;
    }
    if (!activeTaskId || !processed.some((item) => item.id === activeTaskId)) {
      setActiveTaskId(processed[0].id);
    }
  }, [processed, activeTaskId]);

  const activeTask = processed.find((item) => item.id === activeTaskId) ?? null;
  const selectedClusterName =
    cluster && cluster !== "all" ? clusterMap.get(cluster) ?? "Selected cluster" : "All clusters";
  const activeTaskClusterName = activeTask ? clusterMap.get(activeTask.cluster_id) ?? activeTask.cluster_id.slice(0, 8) : "";
  const activeQueueConfig = QUEUES.find((queue) => queue.id === activeQueue) ?? QUEUES[0];

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (
        e.target instanceof HTMLInputElement ||
        e.target instanceof HTMLSelectElement ||
        e.target instanceof HTMLTextAreaElement
      ) {
        return;
      }

      const currentIndex = processed.findIndex((item) => item.id === activeTaskId);
      if (e.key === "j" && processed.length > 0) {
        const nextIndex = Math.min(currentIndex < 0 ? 0 : currentIndex + 1, processed.length - 1);
        setActiveTaskId(processed[nextIndex].id);
        lastKeyboardNavRef.current = Date.now();
      }
      if (e.key === "k" && processed.length > 0) {
        const nextIndex = Math.max(currentIndex < 0 ? 0 : currentIndex - 1, 0);
        setActiveTaskId(processed[nextIndex].id);
        lastKeyboardNavRef.current = Date.now();
      }
      if (e.key === "Enter" && activeTask) router.push(`/tasks/${activeTask.id}`);
      if (e.key === "x" && activeTask) toggleSelect(activeTask.id);
      if (e.key === "/") {
        e.preventDefault();
        document.getElementById("task-search")?.focus();
      }

      if (activeTask) {
        if (e.key === "a" && activeTask.status === "ready") {
          actionMutation.mutate({ id: activeTask.id, action: "accept" });
        }
        if (e.key === "s" && (activeTask.status === "accepted" || activeTask.status === "blocked")) {
          actionMutation.mutate({ id: activeTask.id, action: "start" });
        }
        if (e.key === "c" && activeTask.status === "in_progress") {
          actionMutation.mutate({ id: activeTask.id, action: "complete" });
        }
      }
    };

    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [processed, activeTaskId, router, actionMutation, activeTask]);

  return (
    <div className="animate-fade-in">
      <PageHeader
        eyebrow="Investigation inbox"
        title="Tasks"
        description="Triage what surfaced, decide what to act on, and keep the highest-signal operational work visible."
        meta={
          <>
            <Badge variant="outline">{selectedClusterName}</Badge>
            <span>{queueCounts.all ?? allTasks.length} tasks in scope</span>
            <span>{queueCounts.ready ?? 0} ready to triage</span>
            <span>{queueCounts.approval ?? 0} waiting on approval</span>
          </>
        }
      />

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_400px]">
        <div className="space-y-6">
          <div className="rounded-2xl border border-border-default bg-bg-surface px-5 py-5 shadow-card">
            <div className="flex flex-wrap gap-2.5">
            {QUEUES.map((queue) => {
              const active = activeQueue === queue.id;
              const count = queueCounts[queue.id] ?? 0;
              return (
                <Button
                  key={queue.id}
                  variant="ghost"
                  size="sm"
                  onClick={() => setStatusFilter(queue.status)}
                  className={cn(
                    "inline-flex items-center gap-2 rounded-xl border px-3 py-2 text-sm transition-colors",
                    active
                      ? "border-accent-brand/45 bg-[linear-gradient(135deg,rgba(244,114,182,0.12),rgba(167,139,250,0.08))] text-text-primary"
                      : "border-border-default bg-bg-elevated/70 text-text-secondary hover:border-accent-brand/25 hover:text-text-primary",
                  )}
                >
                  <span className="font-medium">{queue.label}</span>
                  <span className={cn("rounded-full px-2 py-0.5 font-mono text-xs tabular", active ? "bg-bg-primary/60 text-text-primary" : "bg-bg-primary/50 text-text-tertiary")}>
                    {count}
                  </span>
                </Button>
              );
            })}
            </div>
            <div className="mt-4 text-sm text-text-secondary">
              <span className="font-medium text-text-primary">{activeQueueConfig.label}:</span>{" "}
              {activeQueueConfig.description}
            </div>
          </div>

          <div className="rounded-2xl border border-border-default bg-bg-surface/90 px-5 py-5 shadow-card">
            <div className="flex flex-col gap-3 lg:flex-row lg:items-center">
              <div className="relative w-full lg:max-w-[320px]">
                <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-text-tertiary" />
                <Input
                  id="task-search"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Search titles, reasons, labels, blocked context..."
                  className="h-10 bg-bg-elevated pl-9 text-sm"
                />
              </div>

              <div className="flex flex-wrap items-center gap-3">
                <Select value={priorityFilter || "all"} onValueChange={(v) => setPriorityFilter(v === "all" ? "" : v)}>
                  <SelectTrigger className="w-full sm:w-[150px] h-9 text-sm" aria-label="Filter tasks by priority">
                    <SelectValue placeholder="All priorities" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All priorities</SelectItem>
                    <SelectItem value="critical">Critical</SelectItem>
                    <SelectItem value="high">High</SelectItem>
                    <SelectItem value="medium">Medium</SelectItem>
                    <SelectItem value="low">Low</SelectItem>
                  </SelectContent>
                </Select>

                <div className="flex items-center gap-2 text-sm text-text-tertiary">
                  <ArrowUpDown size={14} />
                  <Select value={sortMode} onValueChange={(v) => setSortMode(v as SortMode)}>
                    <SelectTrigger className="w-[170px] h-9 text-sm">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="urgency">Sort by urgency</SelectItem>
                      <SelectItem value="priority">Sort by priority</SelectItem>
                      <SelectItem value="newest">Newest first</SelectItem>
                      <SelectItem value="oldest">Oldest first</SelectItem>
                      <SelectItem value="confidence">Highest confidence</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                {(statusFilter || priorityFilter || searchQuery) ? (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => {
                      setStatusFilter("");
                      setPriorityFilter("");
                      setSearchQuery("");
                    }}
                    className="h-9 text-xs"
                  >
                    Reset filters
                  </Button>
                ) : null}
              </div>

              <div className="text-xs font-mono text-text-tertiary lg:ml-auto">
                {processed.length} visible / {allTasks.length} total
              </div>
            </div>
          </div>

          {selectedIds.size > 0 ? (
            <div className="rounded-2xl border border-border-default bg-bg-elevated px-4 py-3 shadow-card">
              <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
                <div className="text-sm font-semibold text-text-primary">
                  {selectedIds.size} selected
                </div>
                <div className="flex flex-wrap gap-2">
                  <Button size="sm" variant="outline" onClick={() => bulkMutation.mutate("accepted")} disabled={bulkMutation.isPending}>
                    Accept all
                  </Button>
                  <Button size="sm" variant="outline" onClick={() => bulkMutation.mutate("done")} disabled={bulkMutation.isPending}>
                    Complete all
                  </Button>
                  <Button size="sm" variant="ghost" onClick={() => setSelectedIds(new Set())}>
                    Clear
                  </Button>
                </div>
              </div>
            </div>
          ) : null}

          {isLoading ? (
            <div className="flex flex-col gap-3">
              {[1, 2, 3, 4].map((i) => (
                <div key={i} className="skeleton h-[150px] rounded-2xl" />
              ))}
            </div>
          ) : null}

          {error ? (
            <div className="rounded-2xl border border-status-blocked/30 bg-status-blocked/10 px-4 py-3 text-sm text-status-blocked">
              Failed to load tasks: {error.message}
            </div>
          ) : null}

          {!isLoading && !error && processed.length === 0 ? (
            <EmptyState
              eyebrow="Queue is clear"
              icon={<CheckSquare size={20} />}
              title={searchQuery ? "No tasks match this search." : "Nothing needs your attention."}
              description={
                searchQuery
                  ? "Try a different phrase or reset the active filters to widen the queue."
                  : "The Brain is watching your clusters. When issues need triage, they will appear here."
              }
              action={!searchQuery && items.length === 0 ? <Link href="/settings">Configure clusters</Link> : undefined}
            />
          ) : null}

          {!isLoading && !error && processed.length > 0 ? (
            <div className="space-y-5">
              {processed.map((item) => {
                const active = item.id === activeTaskId;
                const clusterName = clusterMap.get(item.cluster_id) ?? item.cluster_id.slice(0, 8);
                const visibleLabels = getVisibleLabels(item);
                const extraLabelCount = Math.max(0, Object.keys(item.labels).length - visibleLabels.length);
                return (
                  <article
                    key={item.id}
                    className={cn(
                      "group rounded-2xl border border-border-default bg-bg-surface px-5 py-5 shadow-card transition-all duration-150",
                      active
                        ? "border-accent-brand/35 bg-bg-elevated shadow-[0_0_22px_rgba(244,114,182,0.04)]"
                        : "hover:border-accent-brand/20 hover:bg-bg-elevated",
                    )}
                    onClick={() => setActiveTaskId(item.id)}
                    onMouseEnter={() => handleMouseEnter(item.id)}
                  >
                    <div className="flex gap-3">
                      <Button
                        variant="ghost"
                        size="icon"
                        role="checkbox"
                        aria-checked={selectedIds.has(item.id)}
                        aria-label={`Select task: ${item.title}`}
                        onClick={(e) => {
                          e.stopPropagation();
                          toggleSelect(item.id);
                        }}
                        className={cn(
                          "mt-0.5 h-5 w-5 shrink-0 rounded-full border p-0 transition-colors",
                          selectedIds.has(item.id)
                            ? "border-accent-brand bg-accent-brand text-text-inverse hover:bg-accent-brand/90"
                            : "border-border-default bg-bg-elevated hover:border-accent-brand/50",
                        )}
                      >
                        {selectedIds.has(item.id) ? <Check size={12} /> : null}
                      </Button>
                      <div className="min-w-0 flex-1 space-y-3">
                        <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
                          <div className="min-w-0 space-y-3">
                            <div className="flex flex-wrap items-center gap-2 text-xs font-semibold uppercase tracking-[0.12em] text-text-tertiary">
                              <Badge variant="outline" className="rounded-full border-border-subtle bg-bg-elevated/80 text-xs text-text-secondary">
                                {clusterName}
                              </Badge>
                              <span className="flex items-center gap-1">
                                <Clock size={12} />
                                {item.created_at ? relativeTime(item.created_at) : "recent"}
                              </span>
                            </div>
                            <div className="space-y-2">
                              <Link href={`/tasks/${item.id}`} className="block text-[15px] font-semibold leading-snug text-text-primary no-underline hover:text-accent-brand">
                                {item.title}
                              </Link>
                              <p className="text-sm leading-relaxed text-text-secondary">
                                {getTaskExcerpt(item)}
                              </p>
                            </div>
                          </div>

                          <div className="flex flex-wrap items-center gap-2">
                            <span className={cn("rounded-full px-2.5 py-1 text-xs font-semibold uppercase tracking-[0.12em] text-white/90", PRIORITY_BG[item.priority])}>
                              {item.priority}
                            </span>
                            <span className={cn("rounded-full px-2.5 py-1 text-xs font-semibold uppercase tracking-[0.12em] text-white/90", STATUS_BG[item.status])}>
                              {item.status.replace(/_/g, " ")}
                            </span>
                            {item.confidence != null ? (
                              <span className={cn("rounded-full border border-border-subtle bg-bg-elevated px-2.5 py-1 font-mono text-xs font-semibold tabular", confColor(item.confidence))}>
                                {Math.round(item.confidence * 100)}%
                              </span>
                            ) : null}
                          </div>
                        </div>

                        <div className="flex flex-wrap items-center gap-2 text-xs">
                          {item.blocked_reason ? (
                            <span
                              className="inline-flex items-center gap-1 rounded-full border border-status-blocked/20 bg-status-blocked/10 px-2 py-1 text-status-blocked"
                            >
                              <Ban size={12} />
                              {item.blocked_reason}
                            </span>
                          ) : null}
                          {item.recommended_next_step ? (
                            <span className="inline-flex items-center gap-1 rounded-full border border-accent-brain/20 bg-[var(--accent-brain-bg)] px-2 py-1 text-text-secondary">
                              <Brain size={12} className="text-accent-brain" />
                              Brain recommendation
                            </span>
                          ) : null}
                          {visibleLabels.map(([k, v]) => (
                            <span
                              key={k}
                              className="rounded-full border border-border-subtle bg-bg-elevated/80 px-2 py-1 font-mono text-xs text-text-tertiary"
                            >
                              {k}={v}
                            </span>
                          ))}
                          {extraLabelCount > 0 ? (
                            <span className="rounded-full border border-border-subtle bg-bg-elevated/80 px-2 py-1 text-xs text-text-tertiary">
                              +{extraLabelCount} more
                            </span>
                          ) : null}
                          {item.annotations?.ticket_url ? (
                            <a
                              href={item.annotations.ticket_url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="inline-flex items-center gap-1 rounded-full border border-border-subtle bg-bg-elevated px-2 py-1 text-xs text-text-secondary no-underline hover:text-accent-brand"
                            >
                              <Link2 size={12} />
                              Ticket linked
                            </a>
                          ) : null}
                          {item.runbook_url ? (
                            <a
                              href={item.runbook_url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="inline-flex items-center gap-1 rounded-full border border-border-subtle bg-bg-elevated px-2 py-1 text-xs text-text-secondary no-underline hover:text-accent-brand"
                            >
                              <ExternalLink size={12} />
                              Runbook
                            </a>
                          ) : null}
                          <Button size="xs" variant="ghost" className="ml-auto" asChild>
                            <Link href={`/tasks/${item.id}`}>
                              Open
                              <ChevronRight size={12} />
                            </Link>
                          </Button>
                        </div>
                      </div>
                    </div>
                  </article>
                );
              })}
            </div>
          ) : null}
        </div>

        <aside className="hidden xl:block">
          <div className="sticky top-6 space-y-4">
            {activeTask ? (
              <TaskPreviewPanel
                task={activeTask}
                clusterName={activeTaskClusterName}
                acting={actionMutation.isPending}
                onAccept={() => actionMutation.mutate({ id: activeTask.id, action: "accept" })}
                onStart={() => actionMutation.mutate({ id: activeTask.id, action: "start" })}
                onComplete={() => actionMutation.mutate({ id: activeTask.id, action: "complete" })}
                onOpen={() => router.push(`/tasks/${activeTask.id}`)}
              />
            ) : (
              <EmptyState
                eyebrow="Inbox preview"
                icon={<Brain size={20} />}
                title="Select a task to inspect it."
                description="Use the queue on the left to triage work, then keep the detail page for deeper investigation."
              />
            )}
          </div>
        </aside>
      </div>
    </div>
  );
}
