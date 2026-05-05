"use client";

import { useState, useMemo, type ReactNode } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import type { Issue, Execution, PaginatedResponse } from "@pinky/contracts";
import { formatDistanceToNow } from "date-fns";
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
import { ClusterBadge } from "@/components/shared/cluster-badge";
import { FadeIn } from "@/components/motion/fade-in";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
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
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { Textarea } from "@/components/ui/textarea";
import { useCluster } from "@/hooks/use-cluster";
import { useSSE } from "@/hooks/use-sse";
import Link from "next/link";
import {
  Activity,
  Eye,
  EyeOff,
  CheckCheck,
  CheckSquare,
  ChevronRight,
  Search,
  Zap,
  Layers,
  VolumeX,
  Sparkles,
  Shield,
  Loader2,
  ArrowUpRight,
  XCircle,
  ThumbsUp,
  ThumbsDown,
  type LucideIcon,
} from "lucide-react";
import { toast } from "sonner";

// ---------------------------------------------------------------------------
// Watch summary type (local — API contract managed by another agent)
// ---------------------------------------------------------------------------

type WatchSummary = {
  since: string;
  signals_processed: number;
  suppressed: number;
  investigating: number;
  tasks_created: number;
  auto_resolved: number;
};

// ---------------------------------------------------------------------------
// MetricCard
// ---------------------------------------------------------------------------

function MetricCard({
  label,
  value,
  icon: Icon,
  color,
}: {
  label: string;
  value: number;
  icon: LucideIcon;
  color?: string;
}) {
  return (
    <Card className="py-3">
      <CardContent className="flex items-center gap-3 px-4 pb-0">
        <Icon size={18} className={cn("shrink-0", color ?? "text-text-secondary")} />
        <div className="min-w-0">
          <p className="text-lg font-semibold tabular-nums text-text-primary">
            {value.toLocaleString()}
          </p>
          <p className="text-xs text-text-tertiary">{label}</p>
        </div>
      </CardContent>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Category definitions
// ---------------------------------------------------------------------------

interface CategoryDef {
  key: string;
  title: string;
  icon: LucideIcon;
  colorClasses: {
    icon: string;
    badge: string;
    dot?: string;
  };
  indicator?: "pulse" | "spinner";
}

const CATEGORIES: CategoryDef[] = [
  {
    key: "analyzing",
    title: "Signals Under Analysis",
    icon: Search,
    colorClasses: {
      icon: "text-purple-500",
      badge: "bg-purple-500/15 text-purple-600",
    },
    indicator: "pulse",
  },
  {
    key: "remediating",
    title: "Auto-Remediations In Progress",
    icon: Zap,
    colorClasses: {
      icon: "text-amber-500",
      badge: "bg-amber-500/15 text-amber-600",
    },
    indicator: "spinner",
  },
  {
    key: "grouped",
    title: "Grouped Issues",
    icon: Layers,
    colorClasses: {
      icon: "text-blue-500",
      badge: "bg-blue-500/15 text-blue-600",
    },
  },
  {
    key: "suppressed",
    title: "Suppressions / Dedup",
    icon: VolumeX,
    colorClasses: {
      icon: "text-text-tertiary",
      badge: "bg-bg-hover text-text-secondary",
    },
  },
  {
    key: "candidates",
    title: "Candidate Task Creation",
    icon: Sparkles,
    colorClasses: {
      icon: "text-purple-500",
      badge: "bg-purple-500/15 text-purple-600",
    },
  },
  {
    key: "approvals",
    title: "Active Executions & Approvals",
    icon: Shield,
    colorClasses: {
      icon: "text-orange-500",
      badge: "bg-orange-500/15 text-orange-600",
    },
  },
];

// ---------------------------------------------------------------------------
// Categorization
// ---------------------------------------------------------------------------

interface CategorizedData {
  analyzing: Issue[];
  remediating: Execution[];
  grouped: Issue[];
  suppressed: Issue[];
  candidates: Issue[];
  approvals: Execution[];
}

function categorize(
  issues: Issue[],
  executions: Execution[],
): CategorizedData {
  const runningInvestigationItemIds = new Set(
    executions
      .filter(
        (e) =>
          e.execution_type === "investigation" &&
          e.status === "running" &&
          e.work_item_id,
      )
      .map((e) => e.work_item_id),
  );

  const analyzingSet = new Set<string>();
  const analyzing = issues.filter((i) => {
    if (
      (i.status === "open" || i.status === "investigating") &&
      runningInvestigationItemIds.has(i.id)
    ) {
      analyzingSet.add(i.id);
      return true;
    }
    return false;
  });

  const remediating = executions.filter(
    (e) => e.execution_type === "remediation" && e.status === "running",
  );

  // Issues with completed investigations are candidates for task creation
  const completedInvestigationItemIds = new Set(
    executions
      .filter(
        (e) =>
          e.execution_type === "investigation" &&
          e.status === "completed" &&
          e.work_item_id,
      )
      .map((e) => e.work_item_id),
  );

  const candidates = issues.filter(
    (i) =>
      i.status === "open" &&
      !analyzingSet.has(i.id) &&
      completedInvestigationItemIds.has(i.id),
  );
  const candidateSet = new Set(candidates.map((i) => i.id));

  const grouped = issues.filter(
    (i) =>
      i.status === "open" &&
      !analyzingSet.has(i.id) &&
      !candidateSet.has(i.id),
  );

  const suppressed = issues.filter((i) => i.status === "suppressed");

  const approvals = executions.filter(
    (e) =>
      e.status === "pending" ||
      e.status === "waiting_for_approval",
  );

  return { analyzing, remediating, grouped, suppressed, candidates, approvals };
}

// ---------------------------------------------------------------------------
// CollapsibleCategory
// ---------------------------------------------------------------------------

function CollapsibleCategory({
  def,
  count,
  defaultOpen,
  children,
}: {
  def: CategoryDef;
  count: number;
  defaultOpen?: boolean;
  children: ReactNode;
}) {
  const [open, setOpen] = useState(defaultOpen ?? count > 0);
  const Icon = def.icon;

  return (
    <Collapsible open={open} onOpenChange={setOpen}>
      <CollapsibleTrigger asChild>
        <button
          type="button"
          className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-left transition-colors hover:bg-bg-hover"
        >
          <ChevronRight
            size={14}
            className={cn(
              "shrink-0 text-text-tertiary transition-transform",
              open && "rotate-90",
            )}
          />
          {def.indicator === "pulse" && count > 0 && (
            <span className="relative flex h-2 w-2 shrink-0">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-purple-400 opacity-75" />
              <span className="relative inline-flex h-2 w-2 rounded-full bg-purple-500" />
            </span>
          )}
          {def.indicator === "spinner" && count > 0 && (
            <Loader2 size={14} className="shrink-0 animate-spin text-amber-500" />
          )}
          <Icon size={16} className={cn("shrink-0", def.colorClasses.icon)} />
          <span className="text-sm font-medium text-text-primary">
            {def.title}
          </span>
          <Badge
            variant="ghost"
            className={cn(
              "ml-auto h-5 min-w-[1.25rem] px-1.5 text-xs font-semibold",
              def.colorClasses.badge,
            )}
          >
            {count}
          </Badge>
        </button>
      </CollapsibleTrigger>
      <CollapsibleContent>
        {count > 0 ? (
          <div className="space-y-1 py-1 pl-7">{children}</div>
        ) : (
          <p className="py-2 pl-7 text-xs text-text-tertiary">
            No items in this category
          </p>
        )}
      </CollapsibleContent>
    </Collapsible>
  );
}

// ---------------------------------------------------------------------------
// Row components
// ---------------------------------------------------------------------------

type IssueCategory = "analyzing" | "grouped" | "suppressed" | "candidates";

function IssueRow({
  issue,
  category,
  onSuppress,
  onResolve,
  onEscalate,
  onInvestigate,
}: {
  issue: Issue;
  category: IssueCategory;
  onSuppress: () => void;
  onResolve: () => void;
  onEscalate: () => void;
  onInvestigate: () => void;
}) {
  const severityConfig = SEVERITY[issue.severity];
  const borderClass = severityConfig?.border ?? "";

  return (
    <div
      className={cn(
        "flex items-center gap-3 rounded-lg border border-border-default border-l-2 bg-bg-surface px-4 py-2.5 transition-colors hover:bg-bg-hover",
        borderClass,
      )}
    >
      <div className="min-w-0 flex-1 space-y-1">
        <p className="truncate text-sm font-medium text-text-primary">
          {issue.title}
        </p>
        <div className="flex flex-wrap items-center gap-2">
          <PriorityBadge priority={issue.severity} />
          <StatusIndicator status={issue.status} />
          <ClusterBadge name={issue.cluster_id} />
          {issue.labels?.scanner && (
            <Badge variant="outline" className="text-xs font-mono">
              {issue.labels.scanner}
            </Badge>
          )}
          {category === "grouped" && issue.labels?.observation_count && (
            <Badge variant="outline" className="text-xs">
              {issue.labels.observation_count} observations
            </Badge>
          )}
          {category === "suppressed" && issue.suppressed_until && (
            <span className="text-xs text-text-tertiary">
              suppressed for{" "}
              {formatDistanceToNow(new Date(issue.suppressed_until))}
            </span>
          )}
          {category === "candidates" && issue.labels?.confidence && (
            <Badge variant="outline" className="text-xs">
              {Math.round(Number(issue.labels.confidence) * 100)}% confidence
            </Badge>
          )}
          <RelativeTime date={issue.last_seen_at} />
        </div>
      </div>

      <div className="flex shrink-0 items-center gap-1">
        {category === "analyzing" && (
          <span className="hidden text-xs text-text-tertiary sm:inline">
            Investigating...
          </span>
        )}

        {/* Suppress button — shown for analyzing & grouped */}
        {(category === "analyzing" || category === "grouped") && (
          <AlertDialog>
            <AlertDialogTrigger asChild>
              <Button
                variant="ghost"
                size="icon"
                className="h-7 w-7 text-text-tertiary"
              >
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
                <AlertDialogAction onClick={onSuppress}>
                  Suppress
                </AlertDialogAction>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>
        )}

        {/* Investigate button — grouped issues */}
        {category === "grouped" && (
          <Button
            variant="ghost"
            size="sm"
            className="h-7 text-xs"
            onClick={onInvestigate}
          >
            <Search size={14} className="mr-1" />
            Investigate
          </Button>
        )}

        {/* Escalate button — suppressed issues */}
        {category === "suppressed" && (
          <Button
            variant="ghost"
            size="sm"
            className="h-7 text-xs"
            onClick={onEscalate}
          >
            <ArrowUpRight size={14} className="mr-1" />
            Escalate
          </Button>
        )}

        {/* Resolve button — analyzing, grouped, candidates */}
        {category !== "suppressed" && (
          <AlertDialog>
            <AlertDialogTrigger asChild>
              <Button
                variant="ghost"
                size="icon"
                className="h-7 w-7 text-text-tertiary"
              >
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
        )}
      </div>
    </div>
  );
}

type ExecCategory = "remediating" | "approvals";

function ExecutionRow({
  execution,
  category,
  onCancel,
  onApprove,
  onReject,
}: {
  execution: Execution;
  category: ExecCategory;
  onCancel: () => void;
  onApprove: () => void;
  onReject: (reason: string) => void;
}) {
  const [rejectOpen, setRejectOpen] = useState(false);
  const [rejectReason, setRejectReason] = useState("");

  const handleReject = () => {
    onReject(rejectReason);
    setRejectReason("");
    setRejectOpen(false);
  };

  return (
    <div className="flex items-center gap-3 rounded-lg border border-border-default bg-bg-surface px-4 py-2.5 transition-colors hover:bg-bg-hover">
      <div className="min-w-0 flex-1 space-y-1">
        <p className="truncate text-sm font-medium text-text-primary">
          {execution.execution_type} execution
        </p>
        <div className="flex flex-wrap items-center gap-2">
          <StatusIndicator status={execution.status} />
          <ClusterBadge name={execution.cluster_id} />
          <span className="text-xs text-text-tertiary">
            {formatDistanceToNow(new Date(execution.created_at), {
              addSuffix: false,
            })}{" "}
            elapsed
          </span>
        </div>
      </div>

      <div className="flex shrink-0 items-center gap-1">
        {/* Cancel — remediating executions */}
        {category === "remediating" && (
          <Button
            variant="ghost"
            size="sm"
            className="h-7 text-xs text-text-tertiary"
            onClick={onCancel}
          >
            <XCircle size={14} className="mr-1" />
            Cancel
          </Button>
        )}

        {/* View Details — remediating executions */}
        {category === "remediating" && execution.work_item_id && (
          <Button variant="ghost" size="sm" className="h-7 text-xs" asChild>
            <Link href={`/tasks/${execution.work_item_id}`}>View Details</Link>
          </Button>
        )}

        {/* Approve/Reject — approvals with waiting_for_approval status */}
        {category === "approvals" &&
          execution.status === "waiting_for_approval" && (
            <>
              <AlertDialog>
                <AlertDialogTrigger asChild>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-7 text-xs text-green-600"
                  >
                    <ThumbsUp size={14} className="mr-1" />
                    Approve
                  </Button>
                </AlertDialogTrigger>
                <AlertDialogContent>
                  <AlertDialogHeader>
                    <AlertDialogTitle>Approve execution?</AlertDialogTitle>
                    <AlertDialogDescription>
                      This will allow the execution to proceed with the
                      proposed changes.
                    </AlertDialogDescription>
                  </AlertDialogHeader>
                  <AlertDialogFooter>
                    <AlertDialogCancel>Cancel</AlertDialogCancel>
                    <AlertDialogAction onClick={onApprove}>
                      Approve
                    </AlertDialogAction>
                  </AlertDialogFooter>
                </AlertDialogContent>
              </AlertDialog>

              <Dialog open={rejectOpen} onOpenChange={setRejectOpen}>
                <DialogTrigger asChild>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-7 text-xs text-red-600"
                  >
                    <ThumbsDown size={14} className="mr-1" />
                    Reject
                  </Button>
                </DialogTrigger>
                <DialogContent>
                  <DialogHeader>
                    <DialogTitle>Reject execution</DialogTitle>
                    <DialogDescription>
                      Provide a reason for rejecting this execution.
                    </DialogDescription>
                  </DialogHeader>
                  <Textarea
                    placeholder="Reason for rejection..."
                    value={rejectReason}
                    onChange={(e) => setRejectReason(e.target.value)}
                    className="min-h-20"
                  />
                  <DialogFooter>
                    <Button
                      variant="outline"
                      onClick={() => setRejectOpen(false)}
                    >
                      Cancel
                    </Button>
                    <Button
                      variant="destructive"
                      onClick={handleReject}
                      disabled={!rejectReason.trim()}
                    >
                      Reject
                    </Button>
                  </DialogFooter>
                </DialogContent>
              </Dialog>
            </>
          )}

        {/* Fallback View link for non-approval pending executions */}
        {category === "approvals" &&
          execution.status !== "waiting_for_approval" && (
            <Button
              variant="ghost"
              size="sm"
              className="shrink-0 text-xs"
              asChild
            >
              <Link href={`/executions/${execution.id}`}>View execution</Link>
            </Button>
          )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main view
// ---------------------------------------------------------------------------

export function WatchView() {
  const clusterId = useCluster();
  const qc = useQueryClient();
  const [search, setSearch] = useState("");
  const [severityFilter, setSeverityFilter] = useState("all");
  const [timeWindow, setTimeWindow] = useState("1h");

  // -- Watch summary --
  const { data: summary } = useQuery({
    queryKey: QUERY_KEYS.watchSummary(timeWindow),
    queryFn: () =>
      api.get<WatchSummary>(
        `/api/v1/analytics/watch-summary?since=${timeWindow}`,
      ),
    staleTime: 30_000,
    refetchInterval: 30_000,
  });

  const { data: issues, isLoading: issuesLoading } = useQuery(
    issuesOptions({
      cluster_id: clusterId ?? undefined,
      severity: severityFilter !== "all" ? severityFilter : undefined,
    }),
  );

  const { data: executions, isLoading: executionsLoading } = useQuery({
    queryKey: QUERY_KEYS.executions({ status: "pending,running,waiting_for_approval" }),
    queryFn: () =>
      api.get<PaginatedResponse<Execution>>(
        "/api/v1/executions?status=pending,running,waiting_for_approval",
      ),
    staleTime: 15_000,
  });

  const { state, lastUpdated } = useSSE("/api/v1/streams/issues", {
    onEvent: {
      update: () => {
        qc.invalidateQueries({ queryKey: QUERY_KEYS.issues() });
        qc.invalidateQueries({ queryKey: QUERY_KEYS.executions() });
        qc.invalidateQueries({ queryKey: QUERY_KEYS.watchSummary() });
      },
    },
  });

  // -- Mutations --

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

  const escalate = useMutation({
    mutationFn: (id: string) => api.post(`/api/v1/issues/${id}/escalate`, {}),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: QUERY_KEYS.issues() });
      toast.success("Issue escalated to investigation");
    },
  });

  const investigate = useMutation({
    mutationFn: (workItemId: string) =>
      api.post("/api/v1/executions", {
        work_item_id: workItemId,
        execution_type: "investigation",
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: QUERY_KEYS.issues() });
      qc.invalidateQueries({ queryKey: QUERY_KEYS.executions() });
      toast.success("Investigation started");
    },
  });

  const cancelExec = useMutation({
    mutationFn: (id: string) => api.post(`/api/v1/executions/${id}/cancel`, {}),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: QUERY_KEYS.executions() });
      toast.info("Execution cancelled");
    },
  });

  const approveExec = useMutation({
    mutationFn: (id: string) =>
      api.post(`/api/v1/executions/${id}/approve`, {}),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: QUERY_KEYS.executions() });
      toast.success("Execution approved");
    },
  });

  const rejectExec = useMutation({
    mutationFn: ({ id, reason }: { id: string; reason: string }) =>
      api.post(`/api/v1/executions/${id}/reject`, { reason }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: QUERY_KEYS.executions() });
      toast.info("Execution rejected");
    },
  });

  const isLoading = issuesLoading || executionsLoading;

  // Categorize data
  const categories = useMemo(
    () =>
      categorize(
        issues?.items ?? [],
        executions?.items ?? [],
      ),
    [issues, executions],
  );

  // Apply search filter across all issue categories
  const applySearch = (items: Issue[]): Issue[] => {
    if (!search) return items;
    const q = search.toLowerCase();
    return items.filter((i) => i.title.toLowerCase().includes(q));
  };

  const applyExecSearch = (items: Execution[]): Execution[] => {
    if (!search) return items;
    const q = search.toLowerCase();
    return items.filter((e) => e.execution_type.toLowerCase().includes(q));
  };

  const filtered = {
    analyzing: applySearch(categories.analyzing),
    remediating: applyExecSearch(categories.remediating),
    grouped: applySearch(categories.grouped),
    suppressed: applySearch(categories.suppressed),
    candidates: applySearch(categories.candidates),
    approvals: applyExecSearch(categories.approvals),
  };

  const totalItems =
    filtered.analyzing.length +
    filtered.remediating.length +
    filtered.grouped.length +
    filtered.suppressed.length +
    filtered.candidates.length +
    filtered.approvals.length;

  return (
    <div className="space-y-4">
      <PageHeader
        title="Watch"
        description="Live issue feed from your fleet"
        actions={
          <StalenessIndicator state={state} lastUpdated={lastUpdated} />
        }
      />

      {/* Activity Summary Strip */}
      {summary && (
        <div className="grid grid-cols-5 gap-3">
          <MetricCard
            label="Signals"
            value={summary.signals_processed}
            icon={Activity}
          />
          <MetricCard
            label="Suppressed"
            value={summary.suppressed}
            icon={VolumeX}
            color="text-text-tertiary"
          />
          <MetricCard
            label="Investigating"
            value={summary.investigating}
            icon={Search}
            color="text-purple-400"
          />
          <MetricCard
            label="Tasks Created"
            value={summary.tasks_created}
            icon={CheckSquare}
            color="text-green-400"
          />
          <MetricCard
            label="Auto-Resolved"
            value={summary.auto_resolved}
            icon={Sparkles}
            color="text-blue-400"
          />
        </div>
      )}

      <SearchFilterBar
        value={search}
        onChange={setSearch}
        placeholder="Search issues..."
        filters={
          <>
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
            <Select value={timeWindow} onValueChange={setTimeWindow}>
              <SelectTrigger className="h-7 w-auto min-w-[60px] border-0 bg-transparent text-xs shadow-none">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="1h">1h</SelectItem>
                <SelectItem value="4h">4h</SelectItem>
                <SelectItem value="24h">24h</SelectItem>
              </SelectContent>
            </Select>
          </>
        }
      />

      {isLoading ? (
        <SkeletonRow rows={6} columns={4} />
      ) : totalItems === 0 ? (
        <EmptyState
          icon={Eye}
          title="No issues found"
          description="All quiet across your fleet"
        />
      ) : (
        <FadeIn>
          <div className="space-y-1">
            {CATEGORIES.map((def) => {
              const key = def.key as keyof typeof filtered;
              const items = filtered[key];
              const count = Array.isArray(items) ? items.length : 0;

              return (
                <CollapsibleCategory
                  key={def.key}
                  def={def}
                  count={count}
                  defaultOpen={count > 0}
                >
                  {key === "remediating"
                    ? (filtered.remediating as Execution[]).map((exec) => (
                        <ExecutionRow
                          key={exec.id}
                          execution={exec}
                          category="remediating"
                          onCancel={() => cancelExec.mutate(exec.id)}
                          onApprove={() => approveExec.mutate(exec.id)}
                          onReject={(reason) =>
                            rejectExec.mutate({ id: exec.id, reason })
                          }
                        />
                      ))
                    : key === "approvals"
                      ? (filtered.approvals as Execution[]).map((exec) => (
                          <ExecutionRow
                            key={exec.id}
                            execution={exec}
                            category="approvals"
                            onCancel={() => cancelExec.mutate(exec.id)}
                            onApprove={() => approveExec.mutate(exec.id)}
                            onReject={(reason) =>
                              rejectExec.mutate({ id: exec.id, reason })
                            }
                          />
                        ))
                      : (items as Issue[]).map((issue) => (
                          <IssueRow
                            key={issue.id}
                            issue={issue}
                            category={key as IssueCategory}
                            onSuppress={() => suppress.mutate(issue.id)}
                            onResolve={() => resolve.mutate(issue.id)}
                            onEscalate={() => escalate.mutate(issue.id)}
                            onInvestigate={() => investigate.mutate(issue.id)}
                          />
                        ))}
                </CollapsibleCategory>
              );
            })}
          </div>
        </FadeIn>
      )}
    </div>
  );
}
