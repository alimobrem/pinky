"use client";

import { useState } from "react";
import { AlertTriangle, ChevronDown, ChevronRight, Filter } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import type { Observation, PaginatedResponse } from "@pinky/contracts";
import { Badge } from "@/components/ui/badge";
import { api } from "@/lib/api";
import { useCluster } from "@/hooks/use-cluster";
import { relativeTime } from "@/lib/format-date";
import { SEVERITY_VARIANT, SEVERITY_BORDER } from "@/lib/status-colors";

export default function AlertsPage() {
  const [severityFilter, setSeverityFilter] = useState("");
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const cluster = useCluster();

  const { data, isLoading, error } = useQuery({
    queryKey: ["alerts", cluster],
    queryFn: () => {
      let url = "/api/v1/alerts";
      if (cluster) url += `?cluster_id=${cluster}`;
      return api.get<PaginatedResponse<Observation>>(url);
    },
  });

  const alerts = data?.items ?? [];
  const filtered = severityFilter ? alerts.filter(a => a.severity === severityFilter) : alerts;

  return (
    <div>
      <div className="flex items-center gap-3 mb-5">
        <AlertTriangle size={20} className="text-text-tertiary" />
        <h1 className="text-lg font-semibold tracking-tight">Alerts</h1>
      </div>

      <div className="flex gap-3 mb-4 items-center">
        <Filter size={14} className="text-text-tertiary" />
        <select value={severityFilter} onChange={e => setSeverityFilter(e.target.value)} className="bg-bg-elevated text-text-primary border border-border-default rounded-md px-2 py-1 text-xs">
          <option value="">All Severities</option>
          <option value="critical">Critical</option>
          <option value="high">High</option>
          <option value="medium">Medium</option>
          <option value="low">Low</option>
        </select>
        <span className="ml-auto text-xs text-text-tertiary">{filtered.length} alerts</span>
      </div>

      {error && <div className="p-3 px-4 mb-4 rounded-md bg-status-blocked/10 border border-status-blocked/30 text-status-blocked text-sm">{error.message}</div>}

      {isLoading && (
        <div className="flex flex-col gap-2">
          {[1, 2, 3].map(i => <div key={i} className="skeleton h-16 rounded-lg" />)}
        </div>
      )}

      {!isLoading && filtered.length === 0 && (
        <div className="flex flex-col items-center py-16 px-6 text-center">
          <div className="font-mono text-xl text-text-tertiary mb-6">(clear)</div>
          <div className="text-[15px] font-semibold mb-2">No active alerts.</div>
          <div className="text-sm text-text-secondary leading-relaxed">Raw signals from your observability stack will appear here when detected.</div>
        </div>
      )}

      {filtered.length > 0 && (
        <div className="flex flex-col gap-2">
          {filtered.map(a => {
            const isExpanded = expandedId === a.id;
            return (
              <div key={a.id} onClick={() => setExpandedId(isExpanded ? null : a.id)}
                className={`bg-bg-surface border border-border-default rounded-xl p-3 px-5 border-l-3 shadow-card transition-all duration-200 ${SEVERITY_BORDER[a.severity] || "border-l-border-default"} cursor-pointer transition-colors hover:bg-bg-hover`}>
                <div className="flex justify-between items-center">
                  <div className="flex items-center gap-3">
                    {isExpanded ? <ChevronDown size={14} className="text-text-tertiary" /> : <ChevronRight size={14} className="text-text-tertiary" />}
                    <span className="font-semibold text-sm">{a.scanner}</span>
                    {a.check_id && <span className="text-text-tertiary text-sm">/ {a.check_id}</span>}
                  </div>
                  <Badge variant={SEVERITY_VARIANT[a.severity] || "outline"} className="uppercase text-[11px]">{a.severity}</Badge>
                </div>
                {a.resource_name && (
                  <div className="text-sm text-text-secondary mt-1 pl-6">
                    <span className="font-mono text-xs">{a.resource_kind}/{a.resource_namespace}/{a.resource_name}</span>
                  </div>
                )}
                <div className="text-[11px] text-text-tertiary mt-1 tabular pl-6">{relativeTime(a.observed_at)}</div>
                {isExpanded && a.payload && Object.keys(a.payload).length > 0 && (
                  <div className="mt-3 pt-3 border-t border-border-subtle pl-6">
                    <div className="text-[11px] font-semibold text-text-tertiary uppercase tracking-wider mb-2">Payload</div>
                    <pre className="text-xs font-mono text-text-secondary bg-bg-elevated p-3 rounded-md overflow-auto max-h-[200px] whitespace-pre-wrap break-words">
                      {JSON.stringify(a.payload, null, 2)}
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
