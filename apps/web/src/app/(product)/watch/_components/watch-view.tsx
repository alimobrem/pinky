"use client";

import { useState, useMemo, type ReactNode } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import type { Issue, Execution, PaginatedResponse, WatchSummary } from "@pinky/contracts";
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
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/components/ui/tabs";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { SignalsTab } from "./signals-tab";
import { useCluster } from "@/hooks/use-cluster";
import { usePaginatedData } from "@/hooks/use-paginated-data";
import { useRetryableMutation } from "@/hooks/use-retryable-mutation";
import Link from "next/link";
import {
  Activity,
  Bell,
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
  Bot,
  Loader2,
  ArrowUpRight,
  ExternalLink,
  XCircle,
  ThumbsUp,
  ThumbsDown,
  type LucideIcon,
} from "lucide-react";
import { toast } from "sonner";


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
    title: "Being Investigated",
    icon: Search,
    colorClasses: {
      icon: "text-purple-500",
      badge: "bg-purple-500/15 text-purple-600",
    },
    indicator: "pulse",
  },
  {
    key: "remediating",
    title: "Remediations Running",
    icon: Zap,
    colorClasses: {
      icon: "text-amber-500",
      badge: "bg-amber-500/15 text-amber-600",
    },
    indicator: "spinner",
  },
  {
    key: "grouped",
    title: "Open Issues",
    icon: Layers,
    colorClasses: {
      icon: "text-blue-500",
      badge: "bg-blue-500/15 text-blue-600",
    },
  },
  {
    key: "suppressed",
    title: "Suppressed",
    icon: VolumeX,
    colorClasses: {
      icon: "text-text-tertiary",
      badge: "bg-bg-hover text-text-secondary",
    },
  },
  {
    key: "candidates",
    title: "Investigation Complete",
    icon: Sparkles,
    colorClasses: {
      icon: "text-purple-500",
      badge: "bg-purple-500/15 text-purple-600",
    },
  },
  {
    key: "approvals",
    title: "Pending Approvals",
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
  const runningInvestigationIssueIds = new Set(
    executions
      .filter(
        (e) =>
          e.execution_type === "investigation" &&
          e.status === "running" &&
          e.issue_id,
      )
      .map((e) => e.issue_id!),
  );

  const analyzingSet = new Set<string>();
  const analyzing = issues.filter((i) => {
    if (
      (i.status === "open" || i.status === "investigating") &&
      runningInvestigationIssueIds.has(i.id)
    ) {
      analyzingSet.add(i.id);
      return true;
    }
    return false;
  });

  const remediating = executions.filter(
    (e) => e.execution_type === "remediation" && e.status === "running",
  );

  const completedInvestigationIssueIds = new Set(
    executions
      .filter(
        (e) =>
          e.execution_type === "investigation" &&
          e.status === "completed" &&
          e.issue_id,
      )
      .map((e) => e.issue_id!),
  );

  const candidates = issues.filter(
    (i) =>
      i.status === "open" &&
      !analyzingSet.has(i.id) &&
      completedInvestigationIssueIds.has(i.id),
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
  disabled,
}: {
  issue: Issue;
  category: IssueCategory;
  onSuppress: (id: string, until: string) => void;
  onResolve: () => void;
  onEscalate: () => void;
  onInvestigate: () => void;
  disabled?: boolean;
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
          <ClusterBadge name={issue.cluster_display_name ?? issue.cluster_id} />
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
          {issue.runbook_url && (
            <a
              href={issue.runbook_url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 text-caption text-brand-pink hover:underline"
              onClick={(e) => e.stopPropagation()}
            >
              Runbook <ExternalLink size={10} />
            </a>
          )}
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
          <Dialog>
            <DialogTrigger asChild>
              <Button
                variant="ghost"
                size="icon"
                className="h-7 w-7"
                title="Suppress"
                disabled={disabled}
              >
                <EyeOff size={14} />
              </Button>
            </DialogTrigger>
            <DialogContent className="max-w-xs">
              <DialogHeader>
                <DialogTitle>Suppress for...</DialogTitle>
              </DialogHeader>
              <div className="flex flex-wrap gap-2">
                {[
                  { label: "1 hour", hours: 1 },
                  { label: "4 hours", hours: 4 },
                  { label: "24 hours", hours: 24 },
                  { label: "7 days", hours: 168 },
                ].map((opt) => (
                  <Button
                    key={opt.hours}
                    variant="outline"
                    size="sm"
                    onClick={() => {
                      const until = new Date(Date.now() + opt.hours * 3600000).toISOString();
                      onSuppress(issue.id, until);
                    }}
                  >
                    {opt.label}
                  </Button>
                ))}
              </div>
            </DialogContent>
          </Dialog>
        )}

        {/* Investigate button — grouped issues */}
        {category === "grouped" && (
          <Button
            variant="ghost"
            size="sm"
            className="h-7 text-xs"
            disabled={disabled}
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
            disabled={disabled}
            onClick={onEscalate}
          >
            <ArrowUpRight size={14} className="mr-1" />
            Escalate
          </Button>
        )}

        {/* Resolve button — grouped, candidates */}
        {category !== "suppressed" && category !== "analyzing" && (
          <AlertDialog>
            <AlertDialogTrigger asChild>
              <Button
                variant="ghost"
                size="icon"
                className="h-7 w-7 text-text-tertiary"
                disabled={disabled}
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
  onReject,
  disabled,
}: {
  execution: Execution;
  category: ExecCategory;
  onCancel: () => void;
  onReject: (reason: string) => void;
  disabled?: boolean;
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
          <ClusterBadge name={execution.cluster_display_name ?? execution.cluster_id} />
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
            disabled={disabled}
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

        {/* Review — approvals with waiting_for_approval status */}
        {category === "approvals" &&
          execution.status === "waiting_for_approval" && (
            <>
              {execution.work_item_id && (
                <Button variant="ghost" size="sm" className="h-7 text-xs text-green-600" asChild>
                  <Link href={`/tasks/${execution.work_item_id}`}>
                    <ThumbsUp size={14} className="mr-1" />
                    Review
                  </Link>
                </Button>
              )}

              <Dialog open={rejectOpen} onOpenChange={setRejectOpen}>
                <DialogTrigger asChild>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-7 text-xs text-red-600"
                    disabled={disabled}
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
  const [namespaceFilter, setNamespaceFilter] = useState("");
  const [issuesCursor, setIssuesCursor] = useState<string | undefined>();

  // -- Watch summary --
  const { data: summary } = useQuery({
    queryKey: QUERY_KEYS.watchSummary(timeWindow),
    queryFn: () =>
      api.get<WatchSummary>(
        `/api/v1/analytics/watch-summary?since=${timeWindow}`,
      ),
    staleTime: 30_000,
  });

  const { data: issues, isLoading: issuesLoading, isFetching: issuesFetching } = useQuery(
    issuesOptions({
      cluster_id: clusterId ?? undefined,
      severity: severityFilter !== "all" ? severityFilter : undefined,
      cursor: issuesCursor,
    }),
  );

  const {
    allItems: allIssues,
    sseState: state,
    lastUpdated,
  } = usePaginatedData(issues, {
    cursor: issuesCursor,
    onReset: () => setIssuesCursor(undefined),
    eventBusId: "watch",
    invalidateKeys: [
      ["issues"],
      ["executions"],
      QUERY_KEYS.watchSummary(),
      ["alerts"],
    ],
  });

  const { data: executions, isLoading: executionsLoading } = useQuery({
    queryKey: QUERY_KEYS.executions({ status: "pending,running,waiting_for_approval" }),
    queryFn: () =>
      api.get<PaginatedResponse<Execution>>(
        "/api/v1/executions?status=pending,running,waiting_for_approval",
      ),
    staleTime: 15_000,
  });

  // -- Mutations --

  const suppress = useRetryableMutation({
    errorMessage: "Failed to suppress issue",
    mutationFn: ({ id, until }: { id: string; until: string }) =>
      api.post(`/api/v1/issues/${id}/suppress`, { until }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["issues"] });
      toast.success("Issue suppressed");
    },
  });

  const resolve = useRetryableMutation({
    errorMessage: "Failed to resolve issue",
    mutationFn: (id: string) => api.post(`/api/v1/issues/${id}/resolve`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["issues"] });
      toast.success("Issue resolved");
    },
  });

  const escalate = useRetryableMutation({
    errorMessage: "Failed to escalate issue",
    mutationFn: (id: string) => api.post(`/api/v1/issues/${id}/escalate`, {}),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["issues"] });
      toast.success("Issue escalated to investigation");
    },
  });

  const investigate = useRetryableMutation({
    errorMessage: "Failed to start investigation",
    mutationFn: (issueId: string) =>
      api.post(`/api/v1/executions?issue_id=${encodeURIComponent(issueId)}&execution_type=investigation`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["issues"] });
      qc.invalidateQueries({ queryKey: ["executions"] });
      toast.success("Investigation started");
    },
  });

  const cancelExec = useRetryableMutation({
    errorMessage: "Failed to cancel execution",
    mutationFn: (id: string) => api.post(`/api/v1/executions/${id}/cancel`, {}),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["executions"] });
      toast.info("Execution cancelled");
    },
  });

  const rejectExec = useRetryableMutation({
    errorMessage: "Failed to reject execution",
    mutationFn: ({ id, reason }: { id: string; reason: string }) =>
      api.post(`/api/v1/executions/${id}/reject`, { reason }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["executions"] });
      toast.info("Execution rejected");
    },
  });

  const anyMutating = suppress.isPending || resolve.isPending || escalate.isPending || investigate.isPending;
  const execMutating = cancelExec.isPending || rejectExec.isPending;

  const isLoading = issuesLoading || executionsLoading;

  // Categorize data
  const categories = useMemo(() => {
    let filteredIssues = allIssues;
    if (namespaceFilter) {
      const ns = namespaceFilter.toLowerCase();
      filteredIssues = filteredIssues.filter((i) => {
        const issueNs = i.labels?.namespace || i.title.split("/")[0] || "";
        return issueNs.toLowerCase().includes(ns);
      });
    }
    return categorize(filteredIssues, executions?.items ?? []);
  }, [allIssues, executions, namespaceFilter]);

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

      <Tabs defaultValue="issues">
        <TabsList className="border-b border-border-default bg-transparent">
          <TabsTrigger value="issues" className="gap-1.5">
            <Eye size={14} />
            Issues ({allIssues.length})
          </TabsTrigger>
          <TabsTrigger value="signals" className="gap-1.5">
            <Bell size={14} />
            Signals
          </TabsTrigger>
        </TabsList>

        <TabsContent value="issues">
          {/* Activity Summary Strip */}
          {summary && (
            <div className="grid grid-cols-3 gap-3 sm:grid-cols-6">
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
              <MetricCard
                label="Operator-Managed"
                value={summary.operator_managed_skipped ?? 0}
                icon={Bot}
                color="text-text-tertiary"
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
                <Input
                  value={namespaceFilter}
                  onChange={(e) => setNamespaceFilter(e.target.value)}
                  placeholder="Namespace..."
                  className="h-7 w-28 border-0 bg-transparent text-body-sm shadow-none placeholder:text-text-tertiary"
                />
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

                              onReject={(reason) =>
                                rejectExec.mutate({ id: exec.id, reason })
                              }
                              disabled={execMutating}
                            />
                          ))
                        : key === "approvals"
                          ? (filtered.approvals as Execution[]).map((exec) => (
                              <ExecutionRow
                                key={exec.id}
                                execution={exec}
                                category="approvals"
                                onCancel={() => cancelExec.mutate(exec.id)}
  
                                onReject={(reason) =>
                                  rejectExec.mutate({ id: exec.id, reason })
                                }
                                disabled={execMutating}
                              />
                            ))
                          : (items as Issue[]).map((issue) => (
                              <IssueRow
                                key={issue.id}
                                issue={issue}
                                category={key as IssueCategory}
                                onSuppress={(id, until) => suppress.mutate({ id, until })}
                                onResolve={() => resolve.mutate(issue.id)}
                                onEscalate={() => escalate.mutate(issue.id)}
                                onInvestigate={() => investigate.mutate(issue.id)}
                                disabled={anyMutating}
                              />
                            ))}
                    </CollapsibleCategory>
                  );
                })}
              </div>
              {(issues?.has_more || issues?.total_count != null) && (
                <div className="flex items-center justify-between pt-3 px-1">
                  {issues?.total_count != null && (
                    <span className="text-caption text-text-tertiary">
                      Showing {allIssues.length} of {issues.total_count}
                    </span>
                  )}
                  {issues?.has_more && (
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => setIssuesCursor(issues.next_cursor ?? undefined)}
                      disabled={issuesFetching && !!issuesCursor}
                      className="ml-auto text-caption"
                    >
                      {issuesFetching && !!issuesCursor ? (
                        <><Loader2 size={12} className="mr-1 animate-spin" />Loading...</>
                      ) : (
                        "Load more"
                      )}
                    </Button>
                  )}
                </div>
              )}
            </FadeIn>
          )}
        </TabsContent>

        <TabsContent value="signals">
          <SignalsTab />
        </TabsContent>
      </Tabs>
    </div>
  );
}
