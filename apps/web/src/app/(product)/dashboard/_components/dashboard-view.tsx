"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import {
  ListTodo,
  Eye,
  CheckCircle2,
  AlertTriangle,
  ShieldAlert,
  Ban,
  Brain,
  ArrowRight,
} from "lucide-react";
import type { WorkItem } from "@pinky/contracts";
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
import { Button } from "@/components/ui/button";
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

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-bold text-text-primary">Dashboard</h1>
        <p className="mt-1 text-[13px] text-text-secondary">
          Fleet overview and active work
        </p>
      </div>

      <FadeIn>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <StatCard
            label="Ready"
            value={readyCount}
            icon={ListTodo}
            color="text-status-ready"
            href="/tasks?status=ready"
          />
          <StatCard
            label="Active"
            value={activeCount}
            icon={CheckCircle2}
            color="text-status-in-progress"
            href="/tasks?status=in_progress"
          />
          <StatCard
            label="Blocked"
            value={blockedCount}
            icon={Ban}
            color="text-status-blocked"
            href="/tasks?status=blocked"
          />
          <StatCard
            label="Needs Approval"
            value={approvalCount}
            icon={ShieldAlert}
            color="text-status-approval"
            href="/tasks?status=waiting_for_approval"
          />
        </div>
      </FadeIn>

      <FadeIn delay={0.05}>
        <div className="grid gap-4 lg:grid-cols-2">
          <Card className="border-border-subtle bg-bg-surface">
            <CardHeader className="flex flex-row items-center justify-between pb-3">
              <CardTitle className="text-sm font-medium text-text-primary">
                <span className="flex items-center gap-2">
                  <Brain size={16} className="text-brand-purple" />
                  Brain Status
                </span>
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-[13px] text-text-secondary">Clusters</span>
                <span className="font-mono text-sm tabular text-text-primary">
                  {clusterList.length}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-[13px] text-text-secondary">Open Issues</span>
                <span className="font-mono text-sm tabular text-text-primary">
                  {issueCount}
                </span>
              </div>
              <div className="flex flex-wrap gap-2 pt-1">
                {clusterList.map((c) => (
                  <span
                    key={c.id}
                    className="inline-flex items-center gap-1.5 rounded-md bg-bg-hover px-2 py-1 text-[11px] text-text-secondary"
                  >
                    <StatusDot status={c.onboarding_state === "ready" ? "done" : "blocked"} />
                    {c.display_name}
                  </span>
                ))}
              </div>
            </CardContent>
          </Card>

          <Card className="border-border-subtle bg-bg-surface">
            <CardHeader className="flex flex-row items-center justify-between pb-3">
              <CardTitle className="text-sm font-medium text-text-primary">
                <span className="flex items-center gap-2">
                  <Eye size={16} className="text-status-blocked" />
                  Open Issues
                </span>
              </CardTitle>
              <Link
                href="/watch"
                className="text-[12px] text-text-tertiary no-underline hover:text-text-secondary"
              >
                View all <ArrowRight size={12} className="inline" />
              </Link>
            </CardHeader>
            <CardContent>
              {issueCount === 0 ? (
                <p className="py-4 text-center text-[13px] text-text-tertiary">
                  No open issues
                </p>
              ) : (
                <div className="space-y-2">
                  {issues?.items?.slice(0, 5).map((issue) => (
                    <div
                      key={issue.id}
                      className="flex items-center gap-2 rounded-md px-2 py-1.5 text-sm hover:bg-bg-hover"
                    >
                      <AlertTriangle
                        size={13}
                        className={cn(
                          issue.severity === "critical" || issue.severity === "high"
                            ? "text-status-blocked"
                            : "text-status-in-progress",
                        )}
                      />
                      <span className="flex-1 truncate text-text-primary">
                        {issue.title}
                      </span>
                      <PriorityBadge priority={issue.severity} size="sm" />
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </FadeIn>

      <FadeIn delay={0.1}>
        <Card className="border-border-subtle bg-bg-surface">
          <CardHeader className="flex flex-row items-center justify-between pb-3">
            <CardTitle className="text-sm font-medium text-text-primary">
              Recent Activity
            </CardTitle>
            <Link
              href="/history"
              className="text-[12px] text-text-tertiary no-underline hover:text-text-secondary"
            >
              View all <ArrowRight size={12} className="inline" />
            </Link>
          </CardHeader>
          <CardContent>
            {!history?.items?.length ? (
              <p className="py-4 text-center text-[13px] text-text-tertiary">
                No recent activity
              </p>
            ) : (
              <div className="space-y-1">
                {history.items.map((event) => (
                  <div
                    key={event.id}
                    className="flex items-center gap-3 rounded-md px-2 py-1.5 text-sm hover:bg-bg-hover"
                  >
                    <StatusDot
                      status={
                        event.event_type.includes("completed") || event.event_type.includes("resolved")
                          ? "done"
                          : event.event_type.includes("failed") || event.event_type.includes("blocked")
                            ? "blocked"
                            : "ready"
                      }
                    />
                    <span className="flex-1 truncate text-text-secondary">
                      {event.event_type.replace(/_/g, " ")}
                    </span>
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

function StatCard({
  label,
  value,
  icon: Icon,
  color,
  href,
}: {
  label: string;
  value: number;
  icon: typeof ListTodo;
  color: string;
  href: string;
}) {
  return (
    <Link href={href} className="no-underline">
      <Card className="border-border-subtle bg-bg-surface transition-colors hover:border-border-default hover:bg-bg-hover">
        <CardContent className="flex items-center gap-3 p-4">
          <div className={cn("rounded-lg bg-bg-hover p-2", color)}>
            <Icon size={18} />
          </div>
          <div>
            <p className="font-mono text-2xl font-bold tabular text-text-primary">
              {value}
            </p>
            <p className="text-[12px] text-text-secondary">{label}</p>
          </div>
        </CardContent>
      </Card>
    </Link>
  );
}
