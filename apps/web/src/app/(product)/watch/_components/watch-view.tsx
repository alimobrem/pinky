"use client";

import { useState, useMemo } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import type { Issue } from "@pinky/contracts";
import { cn } from "@/lib/utils";
import { api } from "@/lib/api";
import { QUERY_KEYS } from "@/lib/constants";
import { issuesOptions } from "../queries";
import { SEVERITY } from "@/lib/status";
import { StatusIndicator } from "@/components/shared/status-indicator";
import { PriorityBadge } from "@/components/shared/priority-badge";
import { RelativeTime } from "@/components/shared/relative-time";
import { StalenessIndicator } from "@/components/shared/staleness-indicator";
import { SearchFilterBar } from "@/components/shared/search-filter-bar";
import { EmptyState } from "@/components/shared/empty-state";
import { SkeletonRow } from "@/components/shared/skeleton-row";
import { PageHeader } from "@/components/shared/page-header";
import { FadeIn } from "@/components/motion/fade-in";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { useCluster } from "@/hooks/use-cluster";
import { useSSE } from "@/hooks/use-sse";
import { Eye, EyeOff, CheckCheck } from "lucide-react";
import { toast } from "sonner";

export function WatchView() {
  const clusterId = useCluster();
  const qc = useQueryClient();
  const [search, setSearch] = useState("");
  const [severityFilter, setSeverityFilter] = useState("all");

  const { data: issues, isLoading } = useQuery(
    issuesOptions({
      cluster_id: clusterId ?? undefined,
      severity: severityFilter !== "all" ? severityFilter : undefined,
    }),
  );

  const { state, lastUpdated } = useSSE("/api/v1/streams/issues", {
    onEvent: {
      update: () => qc.invalidateQueries({ queryKey: QUERY_KEYS.issues() }),
    },
  });

  const suppress = useMutation({
    mutationFn: (id: string) => api.post(`/api/v1/issues/${id}/suppress`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: QUERY_KEYS.issues() });
      toast.success("Issue suppressed");
    },
  });

  const resolve = useMutation({
    mutationFn: (id: string) => api.post(`/api/v1/issues/${id}/resolve`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: QUERY_KEYS.issues() });
      toast.success("Issue resolved");
    },
  });

  const filtered = useMemo(() => {
    if (!search) return issues?.items ?? [];
    const q = search.toLowerCase();
    return (issues?.items ?? []).filter((i) =>
      i.title.toLowerCase().includes(q),
    );
  }, [issues, search]);

  return (
    <div className="space-y-4">
      <PageHeader
        title="Watch"
        description="Live issue feed from your fleet"
        actions={
          <StalenessIndicator state={state} lastUpdated={lastUpdated} />
        }
      />

      <SearchFilterBar
        value={search}
        onChange={setSearch}
        placeholder="Search issues..."
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
        <SkeletonRow rows={6} columns={4} />
      ) : filtered.length === 0 ? (
        <EmptyState
          icon={Eye}
          title="No issues found"
          description="All quiet across your fleet"
        />
      ) : (
        <FadeIn>
          <div className="space-y-2">
            {filtered.map((issue) => (
              <IssueRow
                key={issue.id}
                issue={issue}
                onSuppress={() => suppress.mutate(issue.id)}
                onResolve={() => resolve.mutate(issue.id)}
              />
            ))}
          </div>
        </FadeIn>
      )}
    </div>
  );
}

function IssueRow({
  issue,
  onSuppress,
  onResolve,
}: {
  issue: Issue;
  onSuppress: () => void;
  onResolve: () => void;
}) {
  const severityConfig = SEVERITY[issue.severity];
  const borderClass = severityConfig?.border ?? "";

  return (
    <div
      className={cn(
        "flex items-center gap-3 rounded-lg border border-border-subtle border-l-2 bg-bg-surface px-4 py-3 transition-colors hover:bg-bg-hover",
        borderClass,
      )}
    >
      <div className="min-w-0 flex-1 space-y-1">
        <p className="text-sm font-medium text-text-primary">{issue.title}</p>
        <div className="flex items-center gap-3">
          <PriorityBadge priority={issue.severity} />
          <StatusIndicator status={issue.status} />
          <RelativeTime date={issue.last_seen_at} />
        </div>
      </div>

      <div className="flex items-center gap-1">
        <AlertDialog>
          <AlertDialogTrigger asChild>
            <Button variant="ghost" size="icon" className="h-7 w-7 text-text-tertiary">
              <EyeOff size={14} />
            </Button>
          </AlertDialogTrigger>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>Suppress issue?</AlertDialogTitle>
              <AlertDialogDescription>
                This will hide the issue from the active feed.
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel>Cancel</AlertDialogCancel>
              <AlertDialogAction onClick={onSuppress}>Suppress</AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>

        <AlertDialog>
          <AlertDialogTrigger asChild>
            <Button variant="ghost" size="icon" className="h-7 w-7 text-text-tertiary">
              <CheckCheck size={14} />
            </Button>
          </AlertDialogTrigger>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>Resolve issue?</AlertDialogTitle>
              <AlertDialogDescription>
                Mark this issue as resolved.
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel>Cancel</AlertDialogCancel>
              <AlertDialogAction onClick={onResolve}>Resolve</AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      </div>
    </div>
  );
}
