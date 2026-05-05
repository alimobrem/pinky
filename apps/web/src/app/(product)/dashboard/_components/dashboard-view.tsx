"use client";

import { useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import {
  ListTodo,
  CheckCircle2,
  AlertTriangle,
  ShieldAlert,
  Ban,
  Brain,
  ArrowRight,
  Eye,
  Server,
  ChevronDown,
  ChevronUp,
} from "lucide-react";
import { cn } from "@/lib/utils";
import {
  dashboardTasksOptions,
  dashboardIssuesOptions,
  dashboardHistoryOptions,
  clustersOptions,
} from "../queries";
import { StatusDot } from "@/components/shared/status-indicator";
import { PriorityBadge } from "@/components/shared/priority-badge";
import { RelativeTime } from "@/components/shared/relative-time";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { FadeIn } from "@/components/motion/fade-in";

export function DashboardView() {
  const { data: tasks } = useQuery(dashboardTasksOptions());
  const { data: issues } = useQuery(dashboardIssuesOptions());
  const { data: history } = useQuery(dashboardHistoryOptions());
  const { data: clusters } = useQuery(clustersOptions());

  const items = tasks?.items ?? [];
  const readyCount = items.filter((t) => t.status === "ready").length;
  const activeCount = items.filter((t) =>
    ["accepted", "in_progress"].includes(t.status),
  ).length;
  const blockedCount = items.filter((t) => t.status === "blocked").length;
  const approvalCount = items.filter(
    (t) => t.status === "waiting_for_approval",
  ).length;
  const issueCount = issues?.total_count ?? issues?.items?.length ?? 0;
  const clusterList = clusters?.items ?? [];
  const readyClusters = clusterList.filter((c) => c.onboarding_state === "ready");
  const degradedClusters = clusterList.filter((c) => c.onboarding_state !== "ready");

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-xl font-bold text-text-primary">Dashboard</h1>
        <p className="mt-1 text-body-sm text-text-secondary">
          Fleet overview and active work
        </p>
      </div>

      {/* Stat cards */}
      <FadeIn>
        <div className="grid gap-4 grid-cols-2 lg:grid-cols-4">
          <StatCard label="Ready" value={readyCount} icon={ListTodo} color="text-status-ready" href="/tasks?status=ready" />
          <StatCard label="Active" value={activeCount} icon={CheckCircle2} color="text-status-in-progress" href="/tasks?status=in_progress" />
          <StatCard label="Blocked" value={blockedCount} icon={Ban} color="text-status-blocked" href="/tasks?status=blocked" />
          <StatCard label="Approval" value={approvalCount} icon={ShieldAlert} color="text-status-approval" href="/tasks?status=waiting_for_approval" />
        </div>
      </FadeIn>

      {/* Main grid */}
      <FadeIn delay={0.05}>
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {/* Fleet health — spans 1 col */}
          <Card className="">
            <CardHeader className="pb-2">
              <CardTitle className="flex items-center gap-2 text-xs font-semibold uppercase tracking-widest text-text-tertiary">
                <Server size={14} className="text-brand-purple" />
                Fleet Health
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="flex items-baseline justify-between">
                <span className="font-mono text-3xl font-bold tabular-nums text-text-primary">
                  {clusterList.length}
                </span>
                <span className="text-[12px] text-text-tertiary">clusters</span>
              </div>

              <div className="flex gap-4 text-[12px]">
                <span className="flex items-center gap-1.5">
                  <span className="h-2 w-2 rounded-full bg-status-done" />
                  <span className="text-text-secondary">{readyClusters.length} healthy</span>
                </span>
                {degradedClusters.length > 0 && (
                  <span className="flex items-center gap-1.5">
                    <span className="h-2 w-2 rounded-full bg-status-blocked" />
                    <span className="text-status-blocked">{degradedClusters.length} degraded</span>
                  </span>
                )}
              </div>

              <ClusterList clusters={clusterList} />
            </CardContent>
          </Card>

          {/* Brain status */}
          <Card className="border-l-2 border-l-brand-purple">
            <CardHeader className="pb-2">
              <CardTitle className="flex items-center gap-2 text-xs font-semibold uppercase tracking-widest text-text-tertiary">
                <Brain size={14} className="text-brand-purple" />
                The Brain
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="flex items-center gap-2">
                <span className={cn("h-2.5 w-2.5 rounded-full", clusterList.length > 0 ? "bg-status-done motion-safe:animate-pulse-dot" : "bg-text-tertiary")} />
                <span className="text-sm font-medium text-text-primary">
                  {clusterList.length > 0 ? "Online" : "Idle"}
                </span>
              </div>

              <div className="space-y-2 rounded-lg bg-bg-hover/50 p-3">
                <MetricRow label="Monitoring" value={`${clusterList.length} clusters`} />
                <MetricRow label="Open issues" value={String(issueCount)} valueClass={issueCount > 0 ? "text-status-blocked" : "text-status-done"} />
                <MetricRow label="Active tasks" value={String(readyCount + activeCount + blockedCount + approvalCount)} />
                <MetricRow label="Pending approval" value={String(approvalCount)} valueClass={approvalCount > 0 ? "text-status-approval" : undefined} />
              </div>
            </CardContent>
          </Card>

          {/* Open issues */}
          <Card className="">
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="flex items-center gap-2 text-xs font-semibold uppercase tracking-widest text-text-tertiary">
                <Eye size={14} className="text-status-blocked" />
                Open Issues
              </CardTitle>
              <Link href="/watch" className="text-caption text-text-tertiary no-underline hover:text-text-secondary">
                View all <ArrowRight size={10} className="inline" />
              </Link>
            </CardHeader>
            <CardContent>
              {issueCount === 0 ? (
                <div className="flex flex-col items-center gap-2 py-8 text-center">
                  <div className="rounded-lg bg-status-done/10 p-2">
                    <CheckCircle2 size={18} className="text-status-done" />
                  </div>
                  <p className="text-body-sm text-text-tertiary">All clear</p>
                </div>
              ) : (
                <div className="space-y-1">
                  {issues?.items?.slice(0, 6).map((issue) => (
                    <Link
                      key={issue.id}
                      href="/watch"
                      className="flex items-center gap-2 rounded-md px-2 py-1.5 text-sm no-underline transition-colors hover:bg-bg-hover"
                    >
                      <AlertTriangle
                        size={12}
                        className={cn(
                          issue.severity === "critical" || issue.severity === "high"
                            ? "text-status-blocked"
                            : "text-text-tertiary",
                        )}
                      />
                      <span className="flex-1 truncate text-text-primary">{issue.title}</span>
                      <PriorityBadge priority={issue.severity} size="sm" />
                    </Link>
                  ))}
                  {issueCount > 6 && (
                    <p className="px-2 pt-1 text-caption text-text-tertiary">
                      +{issueCount - 6} more
                    </p>
                  )}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </FadeIn>

      {/* Recent activity */}
      <FadeIn delay={0.1}>
        <Card className="">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-xs font-semibold uppercase tracking-widest text-text-tertiary">
              Recent Activity
            </CardTitle>
            <Link href="/history" className="text-caption text-text-tertiary no-underline hover:text-text-secondary">
              View all <ArrowRight size={10} className="inline" />
            </Link>
          </CardHeader>
          <CardContent>
            {!history?.items?.length ? (
              <p className="py-6 text-center text-body-sm text-text-tertiary">No recent activity</p>
            ) : (
              <div className="space-y-0.5">
                {history.items.map((event) => (
                  <div key={event.id} className="flex items-center gap-3 rounded-md px-2 py-1.5 text-sm transition-colors hover:bg-bg-hover">
                    <StatusDot
                      status={
                        event.event_type.includes("completed") || event.event_type.includes("resolved")
                          ? "done"
                          : event.event_type.includes("failed") || event.event_type.includes("blocked")
                            ? "blocked"
                            : "ready"
                      }
                    />
                    <span className="flex-1 truncate text-text-secondary">{event.event_type.replace(/_/g, " ")}</span>
                    <RelativeTime date={event.occurred_at} />
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </FadeIn>
    </div>
  );
}

function ClusterList({ clusters }: { clusters: { id: string; display_name: string; onboarding_state: string }[] }) {
  const [expanded, setExpanded] = useState(false);
  const COLLAPSED_LIMIT = 5;
  const needsExpand = clusters.length > COLLAPSED_LIMIT;
  const visible = expanded ? clusters : clusters.slice(0, COLLAPSED_LIMIT);

  return (
    <div className="space-y-1">
      {visible.map((c) => (
        <div key={c.id} className="flex items-center gap-2 rounded px-1.5 py-1 text-[12px]">
          <span className={cn("h-1.5 w-1.5 rounded-full shrink-0", c.onboarding_state === "ready" ? "bg-status-done" : "bg-status-blocked")} />
          <span className="truncate text-text-secondary">{c.display_name}</span>
        </div>
      ))}
      {needsExpand && (
        <button
          type="button"
          onClick={() => setExpanded(!expanded)}
          className="flex items-center gap-1 px-1.5 py-1 text-caption text-text-tertiary hover:text-text-secondary"
        >
          {expanded ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
          {expanded ? "Show less" : `+${clusters.length - COLLAPSED_LIMIT} more`}
        </button>
      )}
    </div>
  );
}

function StatCard({ label, value, icon: Icon, color, href }: {
  label: string; value: number; icon: typeof ListTodo; color: string; href: string;
}) {
  return (
    <Link href={href} className="no-underline">
      <Card className="transition-colors hover:border-border-strong hover:bg-bg-hover">
        <CardContent className="flex items-center gap-3 p-4">
          <div className={cn("rounded-lg bg-bg-hover p-2", color)}>
            <Icon size={16} />
          </div>
          <div>
            <p className="font-mono text-xl font-bold tabular-nums text-text-primary">{value}</p>
            <p className="text-caption text-text-secondary">{label}</p>
          </div>
        </CardContent>
      </Card>
    </Link>
  );
}

function MetricRow({ label, value, valueClass }: { label: string; value: string; valueClass?: string }) {
  return (
    <div className="flex items-center justify-between text-body-sm">
      <span className="text-text-tertiary">{label}</span>
      <span className={cn("font-mono tabular-nums text-text-primary", valueClass)}>{value}</span>
    </div>
  );
}
