"use client";

import { useState } from "react";
import Link from "next/link";
import { AlertTriangle, ChevronDown, ChevronRight, Filter } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import type { Observation, PaginatedResponse } from "@pinky/contracts";
import { EmptyState } from "@/components/empty-state";
import { PageHeader } from "@/components/page-header";
import { Badge } from "@/components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { api } from "@/lib/api";
import { useCluster } from "@/hooks/use-cluster";
import { relativeTime } from "@/lib/format-date";
import { SEVERITY_VARIANT, SEVERITY_BORDER } from "@/lib/status-colors";

export default function AlertsPage() {
  const [severityFilter, setSeverityFilter] = useState("all");
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const cluster = useCluster();

  const { data, isLoading, error } = useQuery({
    queryKey: ["alerts", cluster, severityFilter],
    queryFn: () => {
      const params = new URLSearchParams();
      if (cluster) params.set("cluster_id", cluster);
      if (severityFilter && severityFilter !== "all") params.set("severity", severityFilter);
      params.set("limit", "100");
      const url = `/api/v1/alerts?${params.toString()}`;
      return api.get<PaginatedResponse<Observation>>(url);
    },
  });

  const alerts = data?.items ?? [];
  const filtered = alerts;

  return (
    <div className="animate-fade-in">
      <PageHeader
        eyebrow="Raw signal feed"
        title="Alerts"
        description="See the lower-level observations and scanner payloads that inform the higher-signal task inbox."
        meta={<span>{filtered.length} alerts in view</span>}
      />

      <div className="flex flex-wrap items-center gap-3 rounded-2xl border border-border-default bg-bg-surface px-5 py-4 shadow-card">
        <Filter size={14} className="text-text-tertiary" />
        <Select value={severityFilter} onValueChange={setSeverityFilter}>
          <SelectTrigger className="w-[140px] h-8 text-xs" aria-label="Filter alerts by severity">
            <SelectValue placeholder="All Severities" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Severities</SelectItem>
            <SelectItem value="critical">Critical</SelectItem>
            <SelectItem value="high">High</SelectItem>
            <SelectItem value="medium">Medium</SelectItem>
            <SelectItem value="low">Low</SelectItem>
          </SelectContent>
        </Select>
        <span className="ml-auto text-xs text-text-tertiary">{filtered.length} alerts</span>
      </div>

      {error && <div className="mt-4 rounded-2xl border border-status-blocked/30 bg-status-blocked/10 px-4 py-3 text-sm text-status-blocked">{error.message}</div>}

      {isLoading && (
        <div className="mt-4 flex flex-col gap-4">
          {[1, 2, 3, 4].map(i => <div key={i} className="skeleton h-20 rounded-2xl" />)}
        </div>
      )}

      {!isLoading && filtered.length === 0 && (
        <EmptyState
          className="mt-4"
          eyebrow="Raw feed is clear"
          icon={<AlertTriangle size={20} />}
          title="No active alerts."
          description="Lower-level observation signals from your scanners will appear here as soon as they are detected."
          action={<Link href="/settings">Connect a cluster →</Link>}
        />
      )}

      {filtered.length > 0 && (
        <div className="mt-4 flex flex-col gap-4">
          {filtered.map(a => {
            const isExpanded = expandedId === a.id;
            return (
              <div key={a.id} onClick={() => setExpandedId(isExpanded ? null : a.id)}
                className={`cursor-pointer rounded-2xl border border-border-default border-l-[3px] bg-bg-surface p-4 shadow-card transition-all duration-200 hover:bg-bg-hover hover:shadow-card-hover sm:px-5 ${SEVERITY_BORDER[a.severity] || "border-l-border-default"}`}>
                <div className="flex justify-between items-center">
                  <div className="flex items-center gap-3">
                    {isExpanded ? <ChevronDown size={14} className="text-text-tertiary" /> : <ChevronRight size={14} className="text-text-tertiary" />}
                    <span className="font-semibold text-sm">{a.scanner}</span>
                    {a.check_id && <span className="text-text-tertiary text-sm">/ {a.check_id}</span>}
                  </div>
                  <Badge variant={SEVERITY_VARIANT[a.severity] || "outline"} className="uppercase text-xs">{a.severity}</Badge>
                </div>
                {a.resource_name && (
                  <div className="text-sm text-text-secondary mt-1 pl-6">
                    <span className="font-mono text-xs">{a.resource_kind}/{a.resource_namespace}/{a.resource_name}</span>
                  </div>
                )}
                <div className="text-xs text-text-tertiary mt-1 tabular pl-6">{relativeTime(a.observed_at)}</div>
                {isExpanded && a.payload && Object.keys(a.payload).length > 0 && (
                  <div className="mt-3 pt-3 border-t border-border-subtle pl-6">
                    <div className="text-xs font-semibold text-text-tertiary uppercase tracking-wider mb-2">Payload</div>
                    <pre className="max-h-[200px] overflow-auto whitespace-pre-wrap break-words rounded-xl bg-bg-elevated p-3 font-mono text-xs text-text-secondary">
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
