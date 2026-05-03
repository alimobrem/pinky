"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Clock, Filter } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import type { HistoryEvent, PaginatedResponse } from "@pinky/contracts";
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

export default function HistoryPage() {
  const [typeFilter, setTypeFilter] = useState("");
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const cluster = useCluster();
  const router = useRouter();

  const { data, isLoading, error } = useQuery({
    queryKey: ["history", cluster],
    queryFn: () => {
      let url = "/api/v1/history";
      if (cluster) url += `?cluster_id=${cluster}`;
      return api.get<PaginatedResponse<HistoryEvent>>(url);
    },
  });

  const events = data?.items ?? [];
  const filtered = typeFilter ? events.filter(e => e.aggregate_type === typeFilter) : events;
  const types = [...new Set(events.map(e => e.aggregate_type))];

  const handleRowClick = (e: HistoryEvent) => {
    const target = getNavTarget(e);
    if (target) router.push(target);
    else setExpandedId(expandedId === e.id ? null : e.id);
  };

  return (
    <div>
      <div className="flex items-center gap-3 mb-5">
        <Clock size={20} className="text-text-tertiary" />
        <h1 className="text-xl font-semibold tracking-tight">History</h1>
      </div>

      <div className="flex gap-3 mb-4 items-center">
        <Filter size={14} className="text-text-tertiary" />
        <select value={typeFilter} onChange={e => setTypeFilter(e.target.value)} className="bg-bg-elevated text-text-primary border border-border-default rounded-md px-2 py-1 text-xs">
          <option value="">All Types</option>
          {types.map(t => <option key={t} value={t}>{t}</option>)}
        </select>
        <span className="ml-auto text-xs text-text-tertiary">{filtered.length} events</span>
      </div>

      {error && <div className="p-3 px-4 mb-4 rounded-md bg-status-blocked/10 border border-status-blocked/30 text-status-blocked text-sm">{error.message}</div>}

      {isLoading && (
        <div className="flex flex-col gap-2">
          {[1, 2, 3].map(i => <div key={i} className="skeleton h-12 rounded-lg" />)}
        </div>
      )}

      {!isLoading && filtered.length === 0 && (
        <div className="flex flex-col items-center py-16 px-6 text-center">
          <div className="font-mono text-xl text-text-tertiary mb-6">(empty)</div>
          <div className="text-[15px] font-semibold mb-2">No operational history yet.</div>
          <div className="text-sm text-text-secondary leading-relaxed">Completed tasks, remediations, and approvals will appear here over time.</div>
        </div>
      )}

      {filtered.length > 0 && (
        <div className="flex flex-col">
          {filtered.map((e, i) => {
            const navTarget = getNavTarget(e);
            const isExpanded = expandedId === e.id;
            return (
              <div key={e.id}>
                <div
                  onClick={() => handleRowClick(e)}
                  className={cn(
                    "grid grid-cols-[10px_140px_120px_1fr] gap-3 p-3 px-4 items-center transition-colors",
                    navTarget && "cursor-pointer hover:bg-bg-hover",
                    i < filtered.length - 1 && !isExpanded && "border-b border-border-subtle"
                  )}
                >
                  <div className={`w-2 h-2 rounded-full ${TYPE_COLORS[e.aggregate_type] || "bg-text-tertiary"}`} />
                  <span className="font-mono text-xs text-text-tertiary tabular">{relativeTime(e.occurred_at)}</span>
                  <span className={`text-[11px] font-semibold uppercase tracking-wider ${TYPE_TEXT[e.aggregate_type] || "text-text-secondary"}`}>{e.event_type}</span>
                  <span className={navTarget ? "text-sm text-accent-brand" : "text-sm text-text-secondary"}>
                    {e.aggregate_type}/{e.aggregate_id.slice(0, 8)}
                  </span>
                </div>
                {isExpanded && !navTarget && e.payload && Object.keys(e.payload).length > 0 && (
                  <div className={cn("px-4 pb-3 pl-10", i < filtered.length - 1 && "border-b border-border-subtle")}>
                    <pre className="text-xs font-mono text-text-secondary bg-bg-elevated p-3 rounded-md overflow-auto max-h-[200px] whitespace-pre-wrap break-words">
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
