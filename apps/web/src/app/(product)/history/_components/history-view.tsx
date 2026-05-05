"use client";

import { useState, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { historyOptions } from "../queries";
import { DataTable, type Column } from "@/components/shared/data-table";
import { SearchFilterBar } from "@/components/shared/search-filter-bar";
import { EmptyState } from "@/components/shared/empty-state";
import { SkeletonRow } from "@/components/shared/skeleton-row";
import { PageHeader } from "@/components/shared/page-header";
import { StatusDot } from "@/components/shared/status-indicator";
import { RelativeTime } from "@/components/shared/relative-time";
import { FadeIn } from "@/components/motion/fade-in";
import { useCluster } from "@/hooks/use-cluster";
import { Clock } from "lucide-react";
import type { HistoryEvent } from "@pinky/contracts";

const columns: Column<HistoryEvent>[] = [
  {
    id: "time",
    header: "Time",
    sortable: true,
    cell: (e) => <RelativeTime date={e.occurred_at} />,
    className: "w-28",
  },
  {
    id: "type",
    header: "Type",
    cell: (e) => (
      <span className="inline-flex items-center gap-1.5 text-sm">
        <StatusDot
          status={
            e.event_type.includes("completed") || e.event_type.includes("resolved")
              ? "done"
              : e.event_type.includes("failed") || e.event_type.includes("blocked")
                ? "blocked"
                : "ready"
          }
        />
        <span className="text-text-secondary">
          {e.event_type.replace(/_/g, " ")}
        </span>
      </span>
    ),
  },
  {
    id: "aggregate",
    header: "Aggregate",
    cell: (e) => (
      <span className="font-mono text-caption text-text-tertiary">
        {e.aggregate_type} / {e.aggregate_id.slice(0, 8)}
      </span>
    ),
  },
];

export function HistoryView() {
  const clusterId = useCluster();
  const [search, setSearch] = useState("");

  const { data, isLoading } = useQuery(
    historyOptions({ cluster_id: clusterId ?? undefined }),
  );

  const filtered = useMemo(() => {
    const items = data?.items ?? [];
    if (!search) return items;
    const q = search.toLowerCase();
    return items.filter((e) => e.event_type.toLowerCase().includes(q));
  }, [data, search]);

  return (
    <div className="space-y-4">
      <PageHeader title="History" description="Audit trail across your fleet" />

      <SearchFilterBar
        value={search}
        onChange={setSearch}
        placeholder="Filter events..."
      />

      {isLoading ? (
        <SkeletonRow rows={8} columns={3} />
      ) : (
        <FadeIn>
          <DataTable
            data={filtered}
            columns={columns}
            keyFn={(e) => e.id}
            stickyHeader
            emptyState={
              <EmptyState
                icon={Clock}
                title="No events"
                description="History events will appear here as actions occur"
              />
            }
          />
        </FadeIn>
      )}
    </div>
  );
}
