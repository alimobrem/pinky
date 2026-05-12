"use client";

import { use, useMemo, type ReactNode } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import type {
  ClusterNode,
  K8sEvent,
  ClusterNamespace,
  Issue,
  WorkItemStatus,
} from "@pinky/contracts";
import {
  ArrowLeft,
  Server,
  Activity,
  Layers,
  AlertTriangle,
  Calendar,
  Globe,
  Shield,
  Eye,
  Info,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { PageHeader } from "@/components/shared/page-header";
import { DataTable, type Column } from "@/components/shared/data-table";
import { EmptyState } from "@/components/shared/empty-state";
import { StatusDot } from "@/components/shared/status-indicator";
import { StatusIndicator } from "@/components/shared/status-indicator";
import { PriorityBadge } from "@/components/shared/priority-badge";
import { RelativeTime } from "@/components/shared/relative-time";
import { FadeIn } from "@/components/motion/fade-in";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/components/ui/tabs";
import { useEventBus } from "@/hooks/use-event-bus";
import { QUERY_KEYS } from "@/lib/constants";
import { ApiError, ClusterBindingError } from "@/lib/api";
import {
  clusterDetailOptions,
  clusterNodesOptions,
  clusterNamespacesOptions,
  clusterEventsOptions,
  clusterIssuesOptions,
} from "../queries";

export function ClusterDetailView({
  paramsPromise,
}: {
  paramsPromise: Promise<{ id: string }>;
}) {
  const { id } = use(paramsPromise);
  const router = useRouter();
  const qc = useQueryClient();

  useEventBus("cluster-detail", (envelope) => {
    if (envelope.stream === "pinky_watch" && envelope.type === "tool_used") return;
    qc.invalidateQueries({ queryKey: QUERY_KEYS.cluster(id) });
    qc.invalidateQueries({ queryKey: QUERY_KEYS.clusterNodes(id) });
    qc.invalidateQueries({ queryKey: QUERY_KEYS.clusterNamespaces(id) });
    qc.invalidateQueries({ queryKey: QUERY_KEYS.clusterEvents(id) });
    qc.invalidateQueries({ queryKey: QUERY_KEYS.issues({ cluster_id: id }) });
  });

  const {
    data: cluster,
    isLoading: clusterLoading,
    error: clusterError,
  } = useQuery(clusterDetailOptions(id));

  const {
    data: nodesData,
    error: nodesError,
  } = useQuery(clusterNodesOptions(id));

  const {
    data: nsData,
    error: nsError,
  } = useQuery(clusterNamespacesOptions(id));

  const {
    data: eventsData,
    error: eventsError,
  } = useQuery(clusterEventsOptions(id));

  const {
    data: issuesData,
    error: issuesError,
  } = useQuery(clusterIssuesOptions(id));

  const nodes = nodesData?.items ?? [];
  const namespaces = nsData?.items ?? [];
  const events = eventsData?.items ?? [];
  const issues = issuesData?.items ?? [];
  const openIssues = useMemo(
    () => issues.filter((i) => i.status === "open" || i.status === "investigating"),
    [issues],
  );

  if (clusterLoading) {
    return (
      <div className="flex items-center justify-center py-24">
        <span className="text-body-sm text-text-tertiary">Loading...</span>
      </div>
    );
  }

  if (clusterError instanceof ApiError && clusterError.status === 404) {
    return (
      <EmptyState
        icon={Server}
        title="Cluster not found"
        description="This cluster may have been removed."
        action={
          <Button variant="outline" size="sm" onClick={() => router.push("/settings")}>
            Back to settings
          </Button>
        }
      />
    );
  }

  if (!cluster) {
    return (
      <EmptyState
        icon={Server}
        title="Failed to load cluster"
        description="Something went wrong loading cluster details."
      />
    );
  }

  const observerDot: WorkItemStatus =
    cluster.observer_health === "healthy"
      ? "done"
      : cluster.observer_health === "degraded" || cluster.observer_health === "unhealthy"
        ? "blocked"
        : "ready";

  const onboardingDot: WorkItemStatus =
    cluster.onboarding_state === "ready"
      ? "done"
      : cluster.onboarding_state === "degraded"
        ? "blocked"
        : "ready";

  return (
    <div className="space-y-4">
      <button
        type="button"
        onClick={() => router.back()}
        className="inline-flex items-center gap-1 text-caption text-text-tertiary hover:text-text-secondary"
      >
        <ArrowLeft size={12} />
        Back
      </button>

      <PageHeader
        title={cluster.display_name}
        description={cluster.api_endpoint}
        meta={
          <>
            <Badge variant="outline" className="gap-1 text-caption">
              <StatusDot status={onboardingDot} />
              {cluster.onboarding_state}
            </Badge>
            <Badge variant="outline" className="gap-1 text-caption">
              <StatusDot status={observerDot} />
              Observer: {cluster.observer_health}
            </Badge>
          </>
        }
      />

      <Tabs defaultValue="overview">
        <TabsList className="border-b border-border-default bg-transparent">
          <TabsTrigger value="overview" className="gap-1.5">
            <Info size={14} />
            Overview
          </TabsTrigger>
          <TabsTrigger value="nodes" className="gap-1.5">
            <Server size={14} />
            Nodes
          </TabsTrigger>
          <TabsTrigger value="namespaces" className="gap-1.5">
            <Layers size={14} />
            Namespaces
          </TabsTrigger>
          <TabsTrigger value="issues" className="gap-1.5">
            <Eye size={14} />
            Issues
          </TabsTrigger>
          <TabsTrigger value="events" className="gap-1.5">
            <Activity size={14} />
            Events
          </TabsTrigger>
        </TabsList>

        <TabsContent value="overview">
          <OverviewTab
            cluster={cluster}
            nodeCount={nodes.length}
            namespaceCount={namespaces.length}
            issueCount={openIssues.length}
            nodesError={nodesError}
            nsError={nsError}
            observerDot={observerDot}
            onboardingDot={onboardingDot}
          />
        </TabsContent>

        <TabsContent value="nodes">
          <NodesTab nodes={nodes} error={nodesError} />
        </TabsContent>

        <TabsContent value="namespaces">
          <NamespacesTab namespaces={namespaces} error={nsError} />
        </TabsContent>

        <TabsContent value="issues">
          <IssuesTab issues={openIssues} error={issuesError} />
        </TabsContent>

        <TabsContent value="events">
          <EventsTab events={events} error={eventsError} />
        </TabsContent>
      </Tabs>
    </div>
  );
}

/* ── Overview Tab ── */

function OverviewTab({
  cluster,
  nodeCount,
  namespaceCount,
  issueCount,
  nodesError,
  nsError,
  observerDot,
  onboardingDot,
}: {
  cluster: {
    api_endpoint: string;
    onboarding_state: string;
    observer_health: string;
    last_observation_at: string | null;
    created_at: string;
  };
  nodeCount: number;
  namespaceCount: number;
  issueCount: number;
  nodesError: Error | null;
  nsError: Error | null;
  observerDot: WorkItemStatus;
  onboardingDot: WorkItemStatus;
}) {
  return (
    <FadeIn>
      <div className="space-y-6 pt-4">
        <div className="grid gap-4 md:grid-cols-2">
          <InfoCard label="API Endpoint" icon={Globe}>
            <span className="font-mono text-body-sm text-text-primary break-all">
              {cluster.api_endpoint}
            </span>
          </InfoCard>

          <InfoCard label="Onboarding State" icon={Shield}>
            <span className="inline-flex items-center gap-2 text-body-sm text-text-primary">
              <StatusDot status={onboardingDot} />
              {cluster.onboarding_state}
            </span>
          </InfoCard>

          <InfoCard label="Observer Health" icon={Activity}>
            <span className="inline-flex items-center gap-2 text-body-sm text-text-primary">
              <StatusDot status={observerDot} />
              {cluster.observer_health}
            </span>
          </InfoCard>

          <InfoCard label="Last Observation" icon={Eye}>
            {cluster.last_observation_at ? (
              <RelativeTime date={cluster.last_observation_at} className="text-body-sm text-text-primary" />
            ) : (
              <span className="text-body-sm text-text-tertiary">Never</span>
            )}
          </InfoCard>

          <InfoCard label="Created" icon={Calendar}>
            <RelativeTime date={cluster.created_at} className="text-body-sm text-text-primary" />
          </InfoCard>
        </div>

        <div className="flex gap-6">
          <SummaryCount
            label="nodes"
            count={isBindingError(nodesError) ? "—" : nodeCount}
          />
          <SummaryCount
            label="namespaces"
            count={isBindingError(nsError) ? "—" : namespaceCount}
          />
          <SummaryCount
            label="open issues"
            count={issueCount}
            highlight={issueCount > 0}
          />
        </div>
      </div>
    </FadeIn>
  );
}

function InfoCard({
  label,
  icon: Icon,
  children,
}: {
  label: string;
  icon: typeof Globe;
  children: ReactNode;
}) {
  return (
    <Card>
      <CardContent className="flex items-start gap-3 p-4">
        <div className="rounded-lg bg-bg-hover p-2 text-text-tertiary">
          <Icon size={14} />
        </div>
        <div className="min-w-0 space-y-1">
          <p className="text-caption font-medium uppercase tracking-wider text-text-tertiary">
            {label}
          </p>
          {children}
        </div>
      </CardContent>
    </Card>
  );
}

function SummaryCount({
  label,
  count,
  highlight,
}: {
  label: string;
  count: number | string;
  highlight?: boolean;
}) {
  return (
    <div className="flex items-baseline gap-1.5">
      <span
        className={cn(
          "font-mono text-lg font-bold tabular-nums",
          highlight ? "text-status-blocked" : "text-text-primary",
        )}
      >
        {count}
      </span>
      <span className="text-caption text-text-tertiary">{label}</span>
    </div>
  );
}

/* ── Nodes Tab ── */

const NODE_COLUMNS: Column<ClusterNode>[] = [
  {
    id: "name",
    header: "Name",
    cell: (n) => <span className="font-medium text-text-primary">{n.name}</span>,
    sortable: true,
  },
  {
    id: "status",
    header: "Status",
    cell: (n) => (
      <span className="inline-flex items-center gap-1.5">
        <StatusDot status={n.status === "True" ? "done" : "blocked"} />
        <span className={n.status === "True" ? "text-status-done" : "text-status-blocked"}>
          {n.status === "True" ? "Ready" : "NotReady"}
        </span>
      </span>
    ),
  },
  {
    id: "roles",
    header: "Roles",
    cell: (n) =>
      n.roles.length > 0 ? (
        <div className="flex flex-wrap gap-1">
          {n.roles.map((r) => (
            <Badge key={r} variant="outline" className="text-caption">
              {r}
            </Badge>
          ))}
        </div>
      ) : (
        <span className="text-text-tertiary">—</span>
      ),
  },
  {
    id: "version",
    header: "Version",
    cell: (n) => (
      <span className="font-mono text-caption text-text-secondary">
        {n.kubelet_version ?? "—"}
      </span>
    ),
  },
  {
    id: "cpu",
    header: "CPU",
    cell: (n) => (
      <span className="font-mono text-caption tabular-nums text-text-secondary">
        {n.capacity?.cpu ?? "—"}
      </span>
    ),
  },
  {
    id: "memory",
    header: "Memory",
    cell: (n) => (
      <span className="font-mono text-caption tabular-nums text-text-secondary">
        {n.capacity?.memory ?? "—"}
      </span>
    ),
  },
  {
    id: "taints",
    header: "Taints",
    cell: (n) =>
      n.taints.length > 0 ? (
        <Badge variant="outline" className="text-caption tabular-nums">
          {n.taints.length}
        </Badge>
      ) : (
        <span className="text-text-tertiary">0</span>
      ),
  },
  {
    id: "age",
    header: "Age",
    cell: (n) => <RelativeTime date={n.created_at} />,
  },
];

function NodesTab({
  nodes,
  error,
}: {
  nodes: ClusterNode[];
  error: Error | null;
}) {
  if (isBindingError(error)) {
    return <BindingRequiredCard />;
  }

  return (
    <FadeIn>
      <div className="pt-4">
        <DataTable
          data={nodes}
          columns={NODE_COLUMNS}
          keyFn={(n) => n.name}
          emptyState={
            <EmptyState
              icon={Server}
              title="No nodes"
              description="No nodes found in this cluster"
            />
          }
        />
      </div>
    </FadeIn>
  );
}

/* ── Namespaces Tab ── */

const NS_COLUMNS: Column<ClusterNamespace>[] = [
  {
    id: "name",
    header: "Name",
    cell: (ns) => <span className="font-medium text-text-primary">{ns.name}</span>,
    sortable: true,
  },
  {
    id: "status",
    header: "Status",
    cell: (ns) => (
      <Badge variant="outline" className="text-caption">
        {ns.status}
      </Badge>
    ),
  },
  {
    id: "age",
    header: "Age",
    cell: (ns) => <RelativeTime date={ns.created_at} />,
  },
];

function NamespacesTab({
  namespaces,
  error,
}: {
  namespaces: ClusterNamespace[];
  error: Error | null;
}) {
  if (isBindingError(error)) {
    return <BindingRequiredCard />;
  }

  return (
    <FadeIn>
      <div className="pt-4">
        <DataTable
          data={namespaces}
          columns={NS_COLUMNS}
          keyFn={(ns) => ns.name}
          emptyState={
            <EmptyState
              icon={Layers}
              title="No namespaces"
              description="No namespaces found in this cluster"
            />
          }
        />
      </div>
    </FadeIn>
  );
}

/* ── Issues Tab ── */

const ISSUE_COLUMNS: Column<Issue>[] = [
  {
    id: "severity",
    header: "Severity",
    cell: (i) => <PriorityBadge priority={i.severity} size="sm" />,
    className: "w-24",
  },
  {
    id: "title",
    header: "Title",
    cell: (i) => (
      <Link
        href="/watch"
        className="text-text-primary hover:text-brand-purple hover:underline"
      >
        {i.title}
      </Link>
    ),
  },
  {
    id: "status",
    header: "Status",
    cell: (i) => <StatusIndicator status={i.status} />,
  },
  {
    id: "last_seen",
    header: "Last Seen",
    cell: (i) => <RelativeTime date={i.last_seen_at} />,
  },
];

function IssuesTab({
  issues,
  error,
}: {
  issues: Issue[];
  error: Error | null;
}) {
  if (isBindingError(error)) {
    return <BindingRequiredCard />;
  }

  return (
    <FadeIn>
      <div className="pt-4">
        <DataTable
          data={issues}
          columns={ISSUE_COLUMNS}
          keyFn={(i) => i.id}
          emptyState={
            <EmptyState
              icon={AlertTriangle}
              title="No open issues"
              description="No open issues for this cluster"
            />
          }
        />
      </div>
    </FadeIn>
  );
}

/* ── Events Tab ── */

const EVENT_COLUMNS: Column<K8sEvent>[] = [
  {
    id: "type",
    header: "Type",
    cell: (ev) => (
      <Badge
        variant="outline"
        className={cn(
          "text-caption",
          ev.type === "Warning"
            ? "border-status-blocked/30 text-status-blocked"
            : "text-text-tertiary",
        )}
      >
        {ev.type}
      </Badge>
    ),
    className: "w-24",
  },
  {
    id: "reason",
    header: "Reason",
    cell: (ev) => (
      <span className="font-medium text-text-primary">{ev.reason}</span>
    ),
  },
  {
    id: "object",
    header: "Object",
    cell: (ev) => (
      <span className="font-mono text-caption text-text-secondary">
        {ev.involved_object.kind}/{ev.involved_object.name}
      </span>
    ),
  },
  {
    id: "message",
    header: "Message",
    cell: (ev) => (
      <span className="text-text-secondary" title={ev.message}>
        {ev.message.length > 100
          ? `${ev.message.slice(0, 100)}...`
          : ev.message}
      </span>
    ),
    className: "max-w-xs truncate",
  },
  {
    id: "last_seen",
    header: "Last Seen",
    cell: (ev) =>
      ev.last_timestamp ? (
        <RelativeTime date={ev.last_timestamp} />
      ) : (
        <span className="text-text-tertiary">—</span>
      ),
  },
  {
    id: "count",
    header: "Count",
    cell: (ev) => (
      <span className="font-mono text-caption tabular-nums text-text-secondary">
        {ev.count}
      </span>
    ),
    className: "w-16",
  },
];

function EventsTab({
  events,
  error,
}: {
  events: K8sEvent[];
  error: Error | null;
}) {
  if (isBindingError(error)) {
    return <BindingRequiredCard />;
  }

  return (
    <FadeIn>
      <div className="pt-4">
        <DataTable
          data={events}
          columns={EVENT_COLUMNS}
          keyFn={(ev) => `${ev.reason}-${ev.involved_object.kind}-${ev.involved_object.name}-${ev.last_timestamp ?? ""}-${ev.count}`}
          rowClassName={(ev) =>
            ev.type === "Warning" ? "bg-status-blocked/5" : ""
          }
          emptyState={
            <EmptyState
              icon={Activity}
              title="No events"
              description="No recent events in this cluster"
            />
          }
        />
      </div>
    </FadeIn>
  );
}

/* ── Shared ── */

function BindingRequiredCard() {
  return (
    <FadeIn>
      <Card className="mt-4">
        <CardContent className="flex flex-col items-center gap-3 py-12 text-center">
          <div className="rounded-lg bg-bg-surface p-3">
            <Shield size={20} className="text-text-tertiary" />
          </div>
          <div className="space-y-1">
            <p className="text-sm font-medium text-text-primary">
              Connect to this cluster to view live data
            </p>
            <p className="max-w-sm text-body-sm text-text-secondary">
              A cluster binding is required to query nodes, namespaces, and events.
              Log in to the cluster from the Settings page.
            </p>
          </div>
        </CardContent>
      </Card>
    </FadeIn>
  );
}

function isBindingError(error: Error | null): boolean {
  return error instanceof ClusterBindingError;
}
