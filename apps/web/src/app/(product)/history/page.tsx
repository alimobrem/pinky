"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Clock, Filter } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import type { HistoryEvent, PaginatedResponse } from "@pinky/contracts";
import { EmptyState } from "@/components/empty-state";
import { PageHeader } from "@/components/page-header";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { api } from "@/lib/api";
import { useCluster } from "@/hooks/use-cluster";
import { relativeTime } from "@/lib/format-date";
import { cn } from "@/lib/utils";

const TYPE_COLORS: Record<string, string> = {
  work_item: "bg-accent-brand", execution: "bg-accent-brain", approval: "bg-status-approval",
  cluster: "bg-status-ready", issue: "bg-status-in-progress",
};
const TYPE_TEXT: Record<string, string> = {
  work_item: "text-accent-brand", execution: "text-accent-brain", approval: "text-status-approval",
  cluster: "text-status-ready", issue: "text-status-in-progress",
};

function getNavTarget(e: HistoryEvent): string | null {
  switch (e.aggregate_type) {
    case "work_item": return `/tasks/${e.aggregate_id}`;
    case "execution": {
      const workItemId = e.payload?.work_item_id as string | undefined;
      if (workItemId) return `/tasks/${workItemId}/execution/${e.aggregate_id}`;
      return null;
    }
    default: return null;
  }
}

function getHistoryHeadline(e: HistoryEvent): string {
  return e.event_type.replace(/[._]/g, " ");
}

export default function HistoryPage() {
  const [typeFilter, setTypeFilter] = useState("all");
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const cluster = useCluster();
  const router = useRouter();

  const { data, isLoading, error } = useQuery({
    queryKey: ["history", cluster, typeFilter],
    queryFn: () => {
      const params = new URLSearchParams();
      if (cluster) params.set("cluster_id", cluster);
      if (typeFilter && typeFilter !== "all") params.set("aggregate_type", typeFilter);
      params.set("limit", "100");
      const url = `/api/v1/history?${params.toString()}`;
      return api.get<PaginatedResponse<HistoryEvent>>(url);
    },
  });

  const events = data?.items ?? [];
  const filtered = events;
  const types = [...new Set(events.map(e => e.aggregate_type))];

  const handleRowClick = (e: HistoryEvent) => {
    const target = getNavTarget(e);
    if (target) router.push(target);
    else setExpandedId(expandedId === e.id ? null : e.id);
  };

  return (
    <div className="animate-fade-in">
      <PageHeader
        eyebrow="Operational memory"
        title="History"
        description="Trace what changed across tasks, executions, approvals, and cluster activity without losing the thread."
        meta={<span>{filtered.length} events in view</span>}
      />

      <div className="flex flex-wrap items-center gap-3 rounded-2xl border border-border-default bg-bg-surface px-5 py-4 shadow-card">
        <Filter size={14} className="text-text-tertiary" />
        <Select value={typeFilter} onValueChange={setTypeFilter}>
          <SelectTrigger className="w-[140px] h-8 text-xs" aria-label="Filter history by type">
            <SelectValue placeholder="All Types" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Types</SelectItem>
            {types.map(t => <SelectItem key={t} value={t}>{t}</SelectItem>)}
          </SelectContent>
        </Select>
        <span className="ml-auto text-xs text-text-tertiary">{filtered.length} events</span>
      </div>

      {error && <div className="mt-4 rounded-2xl border border-status-blocked/30 bg-status-blocked/10 px-4 py-3 text-sm text-status-blocked">{error.message}</div>}

      {isLoading && (
        <div className="mt-4 flex flex-col gap-3">
          {[1, 2, 3, 4, 5].map(i => <div key={i} className="skeleton h-14 rounded-2xl" />)}
        </div>
      )}

      {!isLoading && filtered.length === 0 && (
        <EmptyState
          className="mt-4"
          eyebrow="No history yet"
          icon={<Clock size={20} />}
          title="No operational history yet."
          description="Completed tasks, remediations, approvals, and system events will start building a narrative here over time."
          action={<Link href="/tasks">Review tasks →</Link>}
        />
      )}

      {filtered.length > 0 && (
        <div className="mt-4 rounded-2xl border border-border-default bg-bg-surface shadow-card">
          {filtered.map((e, i) => {
            const navTarget = getNavTarget(e);
            const isExpanded = expandedId === e.id;
            return (
              <div key={e.id}>
                <div
                  onClick={() => handleRowClick(e)}
                  className={cn(
                    "grid grid-cols-[10px_1fr] gap-x-3 gap-y-1 p-4 transition-colors sm:grid-cols-[10px_120px_1fr] sm:items-start",
                    navTarget && "cursor-pointer hover:bg-bg-hover",
                    i < filtered.length - 1 && !isExpanded && "border-b border-border-subtle"
                  )}
                >
                  <div className={`w-2 h-2 rounded-full ${TYPE_COLORS[e.aggregate_type] || "bg-text-tertiary"}`} />
                  <span className="col-start-2 font-mono text-xs text-text-tertiary tabular sm:col-start-auto">{relativeTime(e.occurred_at)}</span>
                  <div className="col-start-2 space-y-1 sm:col-start-auto">
                    <div className={cn(navTarget ? "text-sm text-accent-brand" : "text-sm text-text-primary")}>
                      {getHistoryHeadline(e)}
                    </div>
                    <div className="flex flex-wrap items-center gap-2 text-xs uppercase tracking-[0.16em] text-text-tertiary">
                      <span className={TYPE_TEXT[e.aggregate_type] || "text-text-secondary"}>{e.aggregate_type}</span>
                      <span>{e.aggregate_id.slice(0, 8)}</span>
                    </div>
                  </div>
                </div>
                {isExpanded && !navTarget && e.payload && Object.keys(e.payload).length > 0 && (
                  <div className={cn("px-4 pb-4 pl-10", i < filtered.length - 1 && "border-b border-border-subtle")}>
                    <pre className="max-h-[200px] overflow-auto whitespace-pre-wrap break-words rounded-xl bg-bg-elevated p-3 font-mono text-xs text-text-secondary">
                      {JSON.stringify(e.payload, null, 2)}
                    </pre>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
