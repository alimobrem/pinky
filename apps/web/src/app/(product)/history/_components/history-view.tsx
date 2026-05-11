"use client";

import { useState, useMemo, useCallback } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { cn } from "@/lib/utils";
import { historyOptions } from "../queries";
import { clustersOptions } from "../../dashboard/queries";
import { useCluster } from "@/hooks/use-cluster";
import { useSSE } from "@/hooks/use-sse";
import { QUERY_KEYS } from "@/lib/constants";
import { SearchFilterBar } from "@/components/shared/search-filter-bar";
import { PageHeader } from "@/components/shared/page-header";
import { EmptyState } from "@/components/shared/empty-state";
import { SkeletonRow } from "@/components/shared/skeleton-row";
import { RelativeTime } from "@/components/shared/relative-time";
import { StatusDot } from "@/components/shared/status-indicator";
import { FadeIn } from "@/components/motion/fade-in";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import { Clock, ChevronRight, Download } from "lucide-react";
import type { HistoryEvent } from "@pinky/contracts";
import type { WorkItemStatus } from "@pinky/contracts";

const EVENT_TYPES = [
  "issue.created",
  "issue.resolved",
  "issue.suppressed",
  "execution.started",
  "execution.completed",
  "execution.failed",
  "work_item.created",
  "work_item.completed",
  "resource.applied",
  "binding.created",
] as const;

function eventTypeToStatus(eventType: string): WorkItemStatus {
  if (eventType.includes("completed") || eventType.includes("resolved"))
    return "done";
  if (eventType.includes("failed") || eventType.includes("blocked"))
    return "blocked";
  return "ready";
}

function EntityLink({ event }: { event: HistoryEvent }) {
  const truncated = event.aggregate_id.slice(0, 8);
  const linkClass =
    "text-accent-brand hover:underline font-mono text-caption truncate max-w-48 inline-block";
  const title = event.aggregate_title;

  switch (event.aggregate_type) {
    case "work_item":
      return (
        <Link href={`/tasks/${event.aggregate_id}`} className={linkClass}>
          {title ?? truncated}
        </Link>
      );
    case "issue": {
      const workItemId = event.payload.work_item_id;
      if (typeof workItemId === "string") {
        return (
          <Link href={`/tasks/${workItemId}`} className={linkClass}>
            {title ?? truncated}
          </Link>
        );
      }
      return (
        <span className="font-mono text-caption text-text-tertiary truncate max-w-48 inline-block">
          {title ?? truncated}
        </span>
      );
    }
    case "execution": {
      const workItemId = event.payload.work_item_id;
      if (typeof workItemId === "string") {
        return (
          <Link
            href={`/tasks/${workItemId}/execution/${event.aggregate_id}`}
            className={linkClass}
          >
            Investigation
          </Link>
        );
      }
      return (
        <span className="font-mono text-caption text-text-tertiary">
          {truncated}
        </span>
      );
    }
    case "cluster":
      return (
        <Link href={`/clusters/${event.aggregate_id}`} className={linkClass}>
          {title ?? truncated}
        </Link>
      );
    default:
      return (
        <span className="font-mono text-caption text-text-tertiary">
          {truncated}
        </span>
      );
  }
}

export function HistoryView() {
  const clusterId = useCluster();
  const qc = useQueryClient();
  const [search, setSearch] = useState("");
  const [eventType, setEventType] = useState<string>("");
  const [timeWindow, setTimeWindow] = useState("");
  const [expanded, setExpanded] = useState<Set<string>>(new Set());

  const since = useMemo(() => {
    if (!timeWindow) return undefined;
    const ms: Record<string, number> = {
      "1h": 3600000,
      "6h": 21600000,
      "24h": 86400000,
      "7d": 604800000,
    };
    return ms[timeWindow]
      ? new Date(Date.now() - ms[timeWindow]).toISOString()
      : undefined;
  }, [timeWindow]);

  const filters = useMemo(
    () => ({
      cluster_id: clusterId ?? undefined,
      event_type: eventType || undefined,
      since,
    }),
    [clusterId, eventType, since],
  );

  const { data, isLoading, error } = useQuery(historyOptions(filters));

  const { data: clustersData } = useQuery(clustersOptions());

  const clusterMap = useMemo(() => {
    const map = new Map<string, string>();
    for (const c of clustersData?.items ?? []) {
      map.set(c.id, c.display_name);
    }
    return map;
  }, [clustersData]);

  useSSE("/api/v1/streams/events", {
    onEvent: {
      update: () => {
        qc.invalidateQueries({ queryKey: ["history"] });
      },
    },
  });

  const allItems = data?.items ?? [];

  const filtered = useMemo(() => {
    if (!search) return allItems;
    const q = search.toLowerCase();
    return allItems.filter(
      (e) =>
        e.event_type.toLowerCase().includes(q) ||
        e.aggregate_type.toLowerCase().includes(q) ||
        (e.principal_id?.toLowerCase().includes(q) ?? false),
    );
  }, [allItems, search]);

  const toggleExpand = useCallback((id: string) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }, []);

  return (
    <div className="space-y-4">
      <PageHeader
        title="History"
        description="Audit trail across your fleet"
        meta={
          <span className="font-mono tabular-nums">{filtered.length} events</span>
        }
        actions={
          <Button
            variant="outline"
            size="sm"
            className="gap-1.5"
            onClick={() => {
              const params = new URLSearchParams();
              if (filters.cluster_id)
                params.set("cluster_id", filters.cluster_id);
              if (filters.event_type)
                params.set("event_type", filters.event_type);
              if (since) params.set("since", since);
              window.open(`/api/v1/history/export?${params}`, "_blank");
            }}
          >
            <Download size={14} />
            Export
          </Button>
        }
      />

      <SearchFilterBar
        value={search}
        onChange={setSearch}
        placeholder="Filter events..."
        filters={
          <>
            <Select
              value={eventType}
              onValueChange={(v) => setEventType(v === "all" ? "" : v)}
            >
              <SelectTrigger size="sm" className="h-7 min-w-[140px] border-0 bg-transparent text-body-sm shadow-none">
                <SelectValue placeholder="All types" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All types</SelectItem>
                {EVENT_TYPES.map((t) => (
                  <SelectItem key={t} value={t}>
                    {t}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Select
              value={timeWindow || "all"}
              onValueChange={(v) => setTimeWindow(v === "all" ? "" : v)}
            >
              <SelectTrigger className="h-7 w-auto min-w-[60px] border-0 bg-transparent text-body-sm shadow-none">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All time</SelectItem>
                <SelectItem value="1h">1h</SelectItem>
                <SelectItem value="6h">6h</SelectItem>
                <SelectItem value="24h">24h</SelectItem>
                <SelectItem value="7d">7d</SelectItem>
              </SelectContent>
            </Select>
          </>
        }
      />

      {isLoading ? (
        <SkeletonRow rows={8} columns={6} />
      ) : error ? (
        <EmptyState
          icon={Clock}
          title="Failed to load history"
          description={error.message}
        />
      ) : filtered.length === 0 ? (
        <EmptyState
          icon={Clock}
          title="No events"
          description="History events will appear here as actions occur"
        />
      ) : (
        <FadeIn>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-28">Time</TableHead>
                <TableHead>Type</TableHead>
                <TableHead className="w-24">Actor</TableHead>
                <TableHead className="w-28">Cluster</TableHead>
                <TableHead className="w-24">Entity</TableHead>
                <TableHead className="w-8" />
              </TableRow>
            </TableHeader>
            <TableBody>
              {filtered.map((event) => {
                const isExpanded = expanded.has(event.id);
                const hasPayload = Object.keys(event.payload).length > 0;

                return (
                  <ExpandableRow
                    key={event.id}
                    event={event}
                    isExpanded={isExpanded}
                    hasPayload={hasPayload}
                    clusterName={
                      event.cluster_id
                        ? clusterMap.get(event.cluster_id) ?? "—"
                        : "—"
                    }
                    onToggle={() => toggleExpand(event.id)}
                  />
                );
              })}
            </TableBody>
          </Table>

          {data?.has_more && (
            <p className="pt-4 text-center text-caption text-text-tertiary">
              Showing first {allItems.length} of {data.total_count} events
            </p>
          )}
        </FadeIn>
      )}
    </div>
  );
}

function ExpandableRow({
  event,
  isExpanded,
  hasPayload,
  clusterName,
  onToggle,
}: {
  event: HistoryEvent;
  isExpanded: boolean;
  hasPayload: boolean;
  clusterName: string;
  onToggle: () => void;
}) {
  return (
    <>
      <TableRow
        className={cn("cursor-pointer", isExpanded && "border-b-0")}
        onClick={onToggle}
      >
        <TableCell className="w-28">
          <RelativeTime date={event.occurred_at} />
        </TableCell>
        <TableCell>
          <span className="inline-flex items-center gap-1.5 text-body-sm">
            <StatusDot status={eventTypeToStatus(event.event_type)} />
            <span className="text-text-secondary">
              {event.description ?? event.event_type.replace(/_/g, " ")}
            </span>
          </span>
        </TableCell>
        <TableCell className="w-24">
          {event.principal_id ? (
            <span className="font-mono text-caption text-text-primary">
              {event.principal_display_name ?? event.principal_id.slice(0, 8)}
            </span>
          ) : (
            <span className="text-caption italic text-text-tertiary">System</span>
          )}
        </TableCell>
        <TableCell className="w-28 text-body-sm text-text-secondary">
          {clusterName}
        </TableCell>
        <TableCell className="w-24">
          <EntityLink event={event} />
        </TableCell>
        <TableCell className="w-8">
          {hasPayload && (
            <ChevronRight
              size={14}
              className={cn(
                "text-text-tertiary transition-transform duration-150",
                isExpanded && "rotate-90",
              )}
            />
          )}
        </TableCell>
      </TableRow>

      {isExpanded && hasPayload && (
        <TableRow className="hover:bg-transparent">
          <TableCell colSpan={6} className="px-2 pb-3 pt-0">
            <pre className="whitespace-pre-wrap text-caption font-mono text-text-secondary rounded-lg bg-bg-elevated p-3 max-h-48 overflow-auto">
              {JSON.stringify(event.payload, null, 2)}
            </pre>
          </TableCell>
        </TableRow>
      )}
    </>
  );
}
