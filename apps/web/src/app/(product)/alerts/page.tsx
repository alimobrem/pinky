"use client";

import { useState } from "react";
import Link from "next/link";
import { AlertTriangle, ChevronDown, ChevronRight, Filter } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import type { Observation, PaginatedResponse } from "@pinky/contracts";
import { EmptyState } from "@/components/empty-state";
import { PageHeader } from "@/components/page-header";
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
    queryKey: ["alerts", cluster, severityFilter],
    queryFn: () => {
      const params = new URLSearchParams();
      if (cluster) params.set("cluster_id", cluster);
      if (severityFilter) params.set("severity", severityFilter);
      params.set("limit", "100");
      const url = `/api/v1/alerts?${params.toString()}`;
      return api.get<PaginatedResponse<Observation>>(url);
    },
  });

  const alerts = data?.items ?? [];
  const filtered = alerts;

  return (
    <div>
      <PageHeader
        eyebrow="Raw signal feed"
        title="Alerts"
        description="See the lower-level observations and scanner payloads that inform the higher-signal task inbox."
        meta={<span>{filtered.length} alerts in view</span>}
      />

      <div className="mt-6 flex flex-wrap items-center gap-3 rounded-2xl border border-border-default bg-bg-surface px-4 py-3 shadow-card">
        <Filter size={14} className="text-text-tertiary" />
        <select aria-label="Filter alerts by severity" value={severityFilter} onChange={e => setSeverityFilter(e.target.value)} className="bg-bg-surface text-text-primary border border-border-default rounded-lg px-2.5 py-1.5 text-xs cursor-pointer hover:border-accent-brain/30 transition-colors focus:outline-none focus:ring-1 focus:ring-ring">
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
        <EmptyState
          className="mt-6"
          eyebrow="Raw feed is clear"
          icon={<AlertTriangle size={20} />}
          title="No active alerts."
          description="Lower-level observation signals from your scanners will appear here as soon as they are detected."
          action={<Link href="/settings">Connect a cluster →</Link>}
        />
      )}

      {filtered.length > 0 && (
        <div className="mt-6 flex flex-col gap-3">
          {filtered.map(a => {
            const isExpanded = expandedId === a.id;
            return (
              <div key={a.id} onClick={() => setExpandedId(isExpanded ? null : a.id)}
                className={`bg-bg-surface border border-border-default rounded-xl border-l-[3px] p-4 sm:px-5 shadow-card transition-all duration-200 ${SEVERITY_BORDER[a.severity] || "border-l-border-default"} cursor-pointer transition-colors hover:bg-bg-hover`}>
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
