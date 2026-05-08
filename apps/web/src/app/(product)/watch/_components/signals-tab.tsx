"use client";

import { useState, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { alertsOptions } from "../queries";
import { SearchFilterBar } from "@/components/shared/search-filter-bar";
import { PriorityBadge } from "@/components/shared/priority-badge";
import { RelativeTime } from "@/components/shared/relative-time";
import { EmptyState } from "@/components/shared/empty-state";
import { SkeletonRow } from "@/components/shared/skeleton-row";
import { FadeIn } from "@/components/motion/fade-in";
import { useCluster } from "@/hooks/use-cluster";
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
import { Bell } from "lucide-react";
import type { Observation } from "@pinky/contracts";

export function SignalsTab() {
  const clusterId = useCluster();
  const [search, setSearch] = useState("");
  const [severityFilter, setSeverityFilter] = useState("all");
  const [expanded, setExpanded] = useState<Set<string>>(new Set());

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

  const toggleExpanded = (id: string) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  return (
    <div className="space-y-4 pt-4">
      <SearchFilterBar
        value={search}
        onChange={setSearch}
        placeholder="Search signals..."
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
      ) : filtered.length === 0 ? (
        <EmptyState
          icon={Bell}
          title="No signals"
          description="Scanner observations will appear here"
        />
      ) : (
        <FadeIn>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-32">Scanner</TableHead>
                <TableHead>Check</TableHead>
                <TableHead className="w-24">Severity</TableHead>
                <TableHead>Resource</TableHead>
                <TableHead className="w-28 text-right">Observed</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filtered.map((o: Observation) => {
                const isExpanded = expanded.has(o.id);
                const hasPayload = o.payload && Object.keys(o.payload).length > 0;
                return (
                  <SignalRow
                    key={o.id}
                    observation={o}
                    isExpanded={isExpanded}
                    hasPayload={hasPayload}
                    onToggle={() => toggleExpanded(o.id)}
                  />
                );
              })}
            </TableBody>
          </Table>
        </FadeIn>
      )}
    </div>
  );
}

function SignalRow({
  observation: o,
  isExpanded,
  hasPayload,
  onToggle,
}: {
  observation: Observation;
  isExpanded: boolean;
  hasPayload: boolean;
  onToggle: () => void;
}) {
  return (
    <>
      <TableRow
        className="cursor-pointer"
        onClick={onToggle}
      >
        <TableCell className="font-mono text-caption text-text-secondary">
          {o.scanner}
        </TableCell>
        <TableCell className="text-body-sm text-text-primary">
          {o.check_id ?? "—"}
        </TableCell>
        <TableCell>
          <PriorityBadge priority={o.severity} />
        </TableCell>
        <TableCell className="font-mono text-caption text-text-tertiary">
          {o.resource_kind
            ? `${o.resource_namespace ?? ""}/${o.resource_name}`
            : "—"}
        </TableCell>
        <TableCell className="text-right">
          <RelativeTime date={o.observed_at} />
        </TableCell>
      </TableRow>
      {isExpanded && hasPayload && (
        <TableRow className="hover:bg-transparent">
          <TableCell colSpan={5} className="px-2 pb-3 pt-0">
            <pre className="whitespace-pre-wrap text-caption font-mono text-text-secondary rounded-lg bg-bg-elevated p-3 max-h-48 overflow-auto">
              {JSON.stringify(o.payload, null, 2)}
            </pre>
          </TableCell>
        </TableRow>
      )}
    </>
  );
}
