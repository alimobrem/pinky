"use client";

import { useState, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { alertsOptions } from "../queries";
import { DataTable, type Column } from "@/components/shared/data-table";
import { SearchFilterBar } from "@/components/shared/search-filter-bar";
import { EmptyState } from "@/components/shared/empty-state";
import { SkeletonRow } from "@/components/shared/skeleton-row";
import { PageHeader } from "@/components/shared/page-header";
import { PriorityBadge } from "@/components/shared/priority-badge";
import { RelativeTime } from "@/components/shared/relative-time";
import { FadeIn } from "@/components/motion/fade-in";
import { useCluster } from "@/hooks/use-cluster";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Bell } from "lucide-react";
import type { Observation } from "@pinky/contracts";

const columns: Column<Observation>[] = [
  {
    id: "scanner",
    header: "Scanner",
    cell: (o) => (
      <span className="font-mono text-xs text-text-secondary">{o.scanner}</span>
    ),
    className: "w-32",
  },
  {
    id: "check",
    header: "Check",
    cell: (o) => (
      <span className="text-sm text-text-primary">{o.check_id ?? "—"}</span>
    ),
  },
  {
    id: "severity",
    header: "Severity",
    sortable: true,
    cell: (o) => <PriorityBadge priority={o.severity} />,
    className: "w-24",
  },
  {
    id: "resource",
    header: "Resource",
    cell: (o) => (
      <span className="font-mono text-[11px] text-text-tertiary">
        {o.resource_kind ? `${o.resource_namespace ?? ""}/${o.resource_name}` : "—"}
      </span>
    ),
  },
  {
    id: "time",
    header: "Observed",
    sortable: true,
    cell: (o) => <RelativeTime date={o.observed_at} />,
    className: "w-28 text-right",
    headerClassName: "text-right",
  },
];

export function AlertsView() {
  const clusterId = useCluster();
  const [search, setSearch] = useState("");
  const [severityFilter, setSeverityFilter] = useState("all");

  const { data, isLoading } = useQuery(
    alertsOptions({
      cluster_id: clusterId ?? undefined,
      severity: severityFilter !== "all" ? severityFilter : undefined,
    }),
  );

  const filtered = useMemo(() => {
    const items = data?.items ?? [];
    if (!search) return items;
    const q = search.toLowerCase();
    return items.filter(
      (o) =>
        o.scanner.toLowerCase().includes(q) ||
        o.check_id?.toLowerCase().includes(q) ||
        o.resource_name?.toLowerCase().includes(q),
    );
  }, [data, search]);

  return (
    <div className="space-y-4">
      <PageHeader
        title="Alerts"
        description="Raw signals from scanners across your fleet"
        meta={
          <span className="font-mono tabular">
            {data?.total_count ?? filtered.length} observations
          </span>
        }
      />

      <SearchFilterBar
        value={search}
        onChange={setSearch}
        placeholder="Search alerts..."
        filters={
          <Select value={severityFilter} onValueChange={setSeverityFilter}>
            <SelectTrigger className="h-7 w-auto min-w-[100px] border-0 bg-transparent text-xs shadow-none">
              <SelectValue placeholder="Severity" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All severities</SelectItem>
              <SelectItem value="critical">Critical</SelectItem>
              <SelectItem value="high">High</SelectItem>
              <SelectItem value="medium">Medium</SelectItem>
              <SelectItem value="low">Low</SelectItem>
            </SelectContent>
          </Select>
        }
      />

      {isLoading ? (
        <SkeletonRow rows={8} />
      ) : (
        <FadeIn>
          <DataTable
            data={filtered}
            columns={columns}
            keyFn={(o) => o.id}
            stickyHeader
            emptyState={
              <EmptyState
                icon={Bell}
                title="No alerts"
                description="Scanner observations will appear here"
              />
            }
          />
        </FadeIn>
      )}
    </div>
  );
}
