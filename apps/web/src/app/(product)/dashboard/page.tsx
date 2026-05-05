"use client";

import Link from "next/link";
import { Brain, CheckSquare, Eye, Clock, AlertTriangle, Shield, ArrowRight } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import type { WorkItem, Issue, HistoryEvent, ClusterRegistryEntry, PaginatedResponse } from "@pinky/contracts";
import { EmptyState } from "@/components/empty-state";
import { PageHeader } from "@/components/page-header";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";
import { relativeTime } from "@/lib/format-date";
import { PRIORITY_BG } from "@/lib/status-colors";

export default function DashboardPage() {
  const { data: tasksData, isLoading: tasksLoading } = useQuery({
    queryKey: ["work-items"],
    queryFn: () => api.get<PaginatedResponse<WorkItem>>("/api/v1/work-items"),
    staleTime: 30_000,
  });

  const { data: issuesData, isLoading: issuesLoading } = useQuery({
    queryKey: ["issues", null],
    queryFn: () => api.get<PaginatedResponse<Issue>>("/api/v1/issues?status=open"),
    staleTime: 30_000,
  });

  const { data: historyData, isLoading: historyLoading } = useQuery({
    queryKey: ["history"],
    queryFn: () => api.get<PaginatedResponse<HistoryEvent>>("/api/v1/history?limit=8"),
    staleTime: 30_000,
  });

  const { data: clustersData, isLoading: clustersLoading } = useQuery({
    queryKey: ["clusters"],
    queryFn: () => api.get<PaginatedResponse<ClusterRegistryEntry>>("/api/v1/clusters"),
    staleTime: 30_000,
  });

  const isLoading = tasksLoading || issuesLoading || historyLoading || clustersLoading;
  const tasks = tasksData?.items ?? [];
  const issues = issuesData?.items ?? [];
  const history = historyData?.items ?? [];
  const clusters = clustersData?.items ?? [];

  const counts = {
    ready: tasks.filter(t => t.status === "ready").length,
    in_progress: tasks.filter(t => t.status === "in_progress" || t.status === "accepted").length,
    blocked: tasks.filter(t => t.status === "blocked").length,
    approval: tasks.filter(t => t.status === "waiting_for_approval").length,
  };
  const pendingApprovals = tasks.filter(t => t.status === "waiting_for_approval");
  const totalActive = counts.ready + counts.in_progress + counts.blocked + counts.approval;

  if (isLoading) {
    return (
      <div className="animate-fade-in space-y-6">
        <div className="skeleton h-[140px] rounded-2xl" />
        <div className="grid grid-cols-1 gap-5 xl:grid-cols-12">
          <div className="skeleton h-[180px] rounded-2xl xl:col-span-5" />
          <div className="skeleton h-[180px] rounded-2xl xl:col-span-4" />
          <div className="skeleton h-[180px] rounded-2xl xl:col-span-3" />
          <div className="skeleton h-[200px] rounded-2xl xl:col-span-7" />
          <div className="skeleton h-[200px] rounded-2xl xl:col-span-5" />
        </div>
      </div>
    );
  }

  return (
    <div className="animate-fade-in">
      <PageHeader
        eyebrow="Operations overview"
        title="Dashboard"
        description="See what needs attention, where it is happening, and whether The Brain is surfacing work that still needs a decision."
        meta={
          <>
            <span>{totalActive} active tasks</span>
            <span>{issues.length} open issues</span>
            <span>{clusters.length} registered clusters</span>
          </>
        }
      />

      <div className="mt-6 grid grid-cols-1 gap-5 xl:grid-cols-12">

        {/* Card 1: Task Summary */}
        <div className="rounded-2xl border border-border-default bg-bg-surface p-5 shadow-card transition-shadow duration-200 hover:shadow-card-hover xl:col-span-5">
          <div className="mb-4 flex items-center justify-between">
            <div className="flex items-center gap-2 text-sm font-semibold text-text-primary">
              <CheckSquare size={15} className="text-accent-brand" />
              Tasks
            </div>
            <Link href="/tasks" className="flex items-center gap-1 text-xs text-accent-brand no-underline hover:underline">
              View all <ArrowRight size={11} />
            </Link>
          </div>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            {[
              { label: "Ready", count: counts.ready, color: "text-status-ready" },
              { label: "Active", count: counts.in_progress, color: "text-status-in-progress" },
              { label: "Blocked", count: counts.blocked, color: "text-status-blocked" },
              { label: "Approval", count: counts.approval, color: "text-status-approval" },
            ].map(s => (
              <div key={s.label} className="rounded-xl border border-border-subtle bg-bg-elevated/60 px-3 py-3 text-center">
                <div className={cn("tabular text-2xl font-bold font-mono", s.color)}>{s.count}</div>
                <div className="mt-1 text-xs text-text-tertiary">{s.label}</div>
              </div>
            ))}
          </div>
        </div>

        {/* Card 2: Cluster Health */}
        <div className="rounded-2xl border border-border-default bg-bg-surface p-5 shadow-card transition-shadow duration-200 hover:shadow-card-hover xl:col-span-4">
          <div className="mb-4 flex items-center justify-between">
            <div className="flex items-center gap-2 text-sm font-semibold text-text-primary">
              <Eye size={15} className="text-accent-brain" />
              Clusters
            </div>
            <Link href="/settings" className="flex items-center gap-1 text-xs text-accent-brand no-underline hover:underline">
              Manage <ArrowRight size={11} />
            </Link>
          </div>
          {clusters.length === 0 ? (
            <EmptyState
              title="No clusters registered."
              description="Add a cluster to start watching live operational data here."
              icon={<Eye size={18} />}
              className="border-none bg-transparent px-0 py-6 shadow-none"
              action={<Link href="/settings">Add one</Link>}
            />
          ) : (
            <div className="flex flex-col gap-2.5">
              {clusters.map(c => {
                const clusterIssues = issues.filter(i => i.cluster_id === c.id).length;
                return (
                  <div key={c.id} className="flex items-center justify-between rounded-lg px-2 py-1.5 transition-colors hover:bg-bg-hover">
                    <div className="flex items-center gap-2">
                      <span className={cn("h-2 w-2 rounded-full", c.onboarding_state === "ready" ? "bg-status-done" : "bg-status-in-progress")} />
                      <span className="text-sm font-medium text-text-primary">{c.display_name}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      {clusterIssues > 0 && <span className="font-mono text-xs text-status-blocked">{clusterIssues} issues</span>}
                      <span className="text-xs text-text-tertiary">{c.onboarding_state}</span>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Card 3: Pending Approvals */}
        <div className="rounded-2xl border border-border-default bg-bg-surface p-5 shadow-card transition-shadow duration-200 hover:shadow-card-hover xl:col-span-3">
          <div className="mb-4 flex items-center justify-between">
            <div className="flex items-center gap-2 text-sm font-semibold text-text-primary">
              <Shield size={15} className="text-status-approval" />
              Pending Approvals
            </div>
            {pendingApprovals.length > 0 && <span className="font-mono text-xs font-semibold text-status-approval">{pendingApprovals.length}</span>}
          </div>
          {pendingApprovals.length === 0 ? (
            <div className="py-4 text-center text-sm text-text-tertiary">No pending approvals</div>
          ) : (
            <div className="flex flex-col gap-1">
              {pendingApprovals.slice(0, 5).map(t => (
                <Link key={t.id} href={`/tasks/${t.id}`} className="group flex items-center justify-between rounded-lg px-2 py-2 no-underline transition-colors hover:bg-bg-hover">
                  <span className="truncate pr-3 text-sm text-text-primary transition-colors group-hover:text-accent-brand">{t.title}</span>
                  <span className={cn("shrink-0 rounded-md px-1.5 py-0.5 text-xs font-semibold uppercase text-white/90", PRIORITY_BG[t.priority])}>{t.priority}</span>
                </Link>
              ))}
            </div>
          )}
        </div>

        {/* Card 4: Active Issues */}
        <div className="rounded-2xl border border-border-default bg-bg-surface p-5 shadow-card transition-shadow duration-200 hover:shadow-card-hover xl:col-span-7">
          <div className="mb-4 flex items-center justify-between">
            <div className="flex items-center gap-2 text-sm font-semibold text-text-primary">
              <AlertTriangle size={15} className="text-status-blocked" />
              Active Issues
            </div>
            <Link href="/watch" className="flex items-center gap-1 text-xs text-accent-brand no-underline hover:underline">
              Watch <ArrowRight size={11} />
            </Link>
          </div>
          {issues.length === 0 ? (
            <div className="py-4 text-center text-sm text-text-tertiary">All quiet</div>
          ) : (
            <div className="flex flex-col gap-1">
              {issues.slice(0, 5).map(i => (
                <Link key={i.id} href="/watch" className="group flex items-center justify-between rounded-lg px-2 py-2 no-underline transition-colors hover:bg-bg-hover">
                  <span className="truncate pr-3 text-sm text-text-primary transition-colors group-hover:text-accent-brand">{i.title}</span>
                  <span className="font-mono text-xs text-text-tertiary">{i.severity}</span>
                </Link>
              ))}
              {issues.length > 5 && <span className="text-center text-xs text-text-tertiary">+{issues.length - 5} more</span>}
            </div>
          )}
        </div>

        {/* Card 5: Recent Activity */}
        <div className="rounded-2xl border border-border-default bg-bg-surface p-5 shadow-card transition-shadow duration-200 hover:shadow-card-hover xl:col-span-5">
          <div className="mb-4 flex items-center justify-between">
            <div className="flex items-center gap-2 text-sm font-semibold text-text-primary">
              <Clock size={15} className="text-text-tertiary" />
              Recent Activity
            </div>
            <Link href="/history" className="flex items-center gap-1 text-xs text-accent-brand no-underline hover:underline">
              History <ArrowRight size={11} />
            </Link>
          </div>
          {history.length === 0 ? (
            <div className="py-4 text-center text-sm text-text-tertiary">No activity yet</div>
          ) : (
            <div className="flex flex-col gap-1">
              {history.slice(0, 6).map(e => (
                <div key={e.id} className="flex items-center gap-2.5 rounded-lg px-2 py-1.5 text-xs transition-colors hover:bg-bg-hover">
                  <span className="w-20 shrink-0 font-mono text-text-tertiary tabular">{relativeTime(e.occurred_at)}</span>
                  <span className="truncate text-text-secondary">{e.event_type}</span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Card 6: Brain Status */}
        <div className="rounded-2xl border border-border-default border-l-[3px] border-l-accent-brain bg-bg-surface p-5 shadow-card shadow-brain-glow xl:col-span-12 2xl:col-span-3">
          <div className="mb-4 flex items-center justify-between">
            <div className="flex items-center gap-2 text-sm font-semibold text-accent-brain">
              <Brain size={15} />
              The Brain
            </div>
            <span className={cn("h-2 w-2 rounded-full", clusters.length > 0 ? "bg-status-done animate-brain-pulse" : "bg-text-tertiary")} />
          </div>
          <div className="space-y-3">
            <div className="flex justify-between text-sm">
              <span className="text-text-tertiary">Status</span>
              <span className="font-medium text-text-primary">
                {clusters.length > 0
                  ? `Online — monitoring ${clusters.length} cluster${clusters.length === 1 ? "" : "s"}`
                  : "Idle — no clusters"}
              </span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-text-tertiary">Clusters</span>
              <span className="font-mono text-text-primary">{clusters.length}</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-text-tertiary">Open issues</span>
              <span className={cn("font-mono", issues.length > 0 ? "text-status-blocked" : "text-status-done")}>{issues.length}</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-text-tertiary">Active tasks</span>
              <span className="font-mono text-text-primary">{totalActive}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
