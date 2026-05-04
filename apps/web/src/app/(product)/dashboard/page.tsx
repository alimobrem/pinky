"use client";

import Link from "next/link";
import { Brain, CheckSquare, Eye, Clock, AlertTriangle, Shield, ArrowRight } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import type { WorkItem, Issue, HistoryEvent, ClusterRegistryEntry, PaginatedResponse } from "@pinky/contracts";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";
import { relativeTime } from "@/lib/format-date";
import { PRIORITY_BG } from "@/lib/status-colors";

export default function DashboardPage() {
  const { data: tasksData } = useQuery({
    queryKey: ["dashboard-tasks"],
    queryFn: () => api.get<PaginatedResponse<WorkItem>>("/api/v1/work-items"),
  });

  const { data: issuesData } = useQuery({
    queryKey: ["dashboard-issues"],
    queryFn: () => api.get<PaginatedResponse<Issue>>("/api/v1/issues?status=open"),
  });

  const { data: historyData } = useQuery({
    queryKey: ["dashboard-history"],
    queryFn: () => api.get<PaginatedResponse<HistoryEvent>>("/api/v1/history?limit=8"),
  });

  const { data: clustersData } = useQuery({
    queryKey: ["dashboard-clusters"],
    queryFn: () => api.get<PaginatedResponse<ClusterRegistryEntry>>("/api/v1/clusters"),
  });

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

  return (
    <div className="animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-xl font-semibold tracking-tight text-text-primary">Dashboard</h1>
          <p className="text-sm text-text-secondary mt-1">{totalActive} active tasks across {clusters.length} clusters</p>
        </div>
        <div className="flex items-center gap-2 text-xs text-text-tertiary">
          <Brain size={14} className="text-accent-brain" />
          <span className="w-1.5 h-1.5 rounded-full bg-status-done animate-brain-pulse" />
          <span className="font-medium">Brain monitoring</span>
        </div>
      </div>

      <div className="grid grid-cols-2 xl:grid-cols-3 gap-5">

        {/* Card 1: Task Summary */}
        <div className="bg-bg-surface border border-border-default rounded-xl p-5 shadow-card">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2 text-sm font-semibold text-text-primary">
              <CheckSquare size={15} className="text-accent-brand" />
              Tasks
            </div>
            <Link href="/tasks" className="text-xs text-accent-brand no-underline hover:underline flex items-center gap-1">
              View all <ArrowRight size={11} />
            </Link>
          </div>
          <div className="grid grid-cols-4 gap-3">
            {[
              { label: "Ready", count: counts.ready, color: "text-status-ready" },
              { label: "Active", count: counts.in_progress, color: "text-status-in-progress" },
              { label: "Blocked", count: counts.blocked, color: "text-status-blocked" },
              { label: "Approval", count: counts.approval, color: "text-status-approval" },
            ].map(s => (
              <div key={s.label} className="text-center">
                <div className={cn("tabular text-2xl font-bold font-mono", s.color)}>{s.count}</div>
                <div className="text-xs text-text-tertiary mt-0.5">{s.label}</div>
              </div>
            ))}
          </div>
        </div>

        {/* Card 2: Cluster Health */}
        <div className="bg-bg-surface border border-border-default rounded-xl p-5 shadow-card">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2 text-sm font-semibold text-text-primary">
              <Eye size={15} className="text-accent-brain" />
              Clusters
            </div>
            <Link href="/settings" className="text-xs text-accent-brand no-underline hover:underline flex items-center gap-1">
              Manage <ArrowRight size={11} />
            </Link>
          </div>
          {clusters.length === 0 ? (
            <div className="text-sm text-text-tertiary py-4 text-center">
              No clusters registered.
              <Link href="/settings" className="text-accent-brand ml-1">Add one →</Link>
            </div>
          ) : (
            <div className="flex flex-col gap-2.5">
              {clusters.map(c => {
                const clusterIssues = issues.filter(i => i.cluster_id === c.id).length;
                return (
                  <div key={c.id} className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className={cn("w-2 h-2 rounded-full", c.onboarding_state === "ready" ? "bg-status-done" : "bg-status-in-progress")} />
                      <span className="text-sm text-text-primary font-medium">{c.display_name}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      {clusterIssues > 0 && <span className="text-xs font-mono text-status-blocked">{clusterIssues} issues</span>}
                      <span className="text-xs text-text-tertiary">{c.onboarding_state}</span>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Card 3: Pending Approvals */}
        <div className="bg-bg-surface border border-border-default rounded-xl p-5 shadow-card">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2 text-sm font-semibold text-text-primary">
              <Shield size={15} className="text-status-approval" />
              Pending Approvals
            </div>
            {pendingApprovals.length > 0 && <span className="text-xs font-mono font-semibold text-status-approval">{pendingApprovals.length}</span>}
          </div>
          {pendingApprovals.length === 0 ? (
            <div className="text-sm text-text-tertiary py-4 text-center">No pending approvals</div>
          ) : (
            <div className="flex flex-col gap-2.5">
              {pendingApprovals.slice(0, 5).map(t => (
                <Link key={t.id} href={`/tasks/${t.id}`} className="flex items-center justify-between no-underline group">
                  <span className="text-sm text-text-primary truncate pr-3 group-hover:text-accent-brand transition-colors">{t.title}</span>
                  <span className={cn("text-xs px-1.5 py-0.5 rounded font-semibold uppercase text-white/90 shrink-0", PRIORITY_BG[t.priority])}>{t.priority}</span>
                </Link>
              ))}
            </div>
          )}
        </div>

        {/* Card 4: Active Issues */}
        <div className="bg-bg-surface border border-border-default rounded-xl p-5 shadow-card">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2 text-sm font-semibold text-text-primary">
              <AlertTriangle size={15} className="text-status-blocked" />
              Active Issues
            </div>
            <Link href="/watch" className="text-xs text-accent-brand no-underline hover:underline flex items-center gap-1">
              Watch <ArrowRight size={11} />
            </Link>
          </div>
          {issues.length === 0 ? (
            <div className="text-sm text-text-tertiary py-4 text-center">All quiet</div>
          ) : (
            <div className="flex flex-col gap-2.5">
              {issues.slice(0, 5).map(i => (
                <div key={i.id} className="flex items-center justify-between">
                  <span className="text-sm text-text-primary truncate pr-3">{i.title}</span>
                  <span className="text-xs font-mono text-text-tertiary">{i.severity}</span>
                </div>
              ))}
              {issues.length > 5 && <span className="text-xs text-text-tertiary text-center">+{issues.length - 5} more</span>}
            </div>
          )}
        </div>

        {/* Card 5: Recent Activity */}
        <div className="bg-bg-surface border border-border-default rounded-xl p-5 shadow-card">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2 text-sm font-semibold text-text-primary">
              <Clock size={15} className="text-text-tertiary" />
              Recent Activity
            </div>
            <Link href="/history" className="text-xs text-accent-brand no-underline hover:underline flex items-center gap-1">
              History <ArrowRight size={11} />
            </Link>
          </div>
          {history.length === 0 ? (
            <div className="text-sm text-text-tertiary py-4 text-center">No activity yet</div>
          ) : (
            <div className="flex flex-col gap-2">
              {history.slice(0, 6).map(e => (
                <div key={e.id} className="flex items-center gap-2.5 text-xs">
                  <span className="font-mono text-text-tertiary tabular shrink-0 w-20">{relativeTime(e.occurred_at)}</span>
                  <span className="text-text-secondary truncate">{e.event_type}</span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Card 6: Brain Status */}
        <div className="bg-bg-surface border border-border-default rounded-xl p-5 shadow-card border-l-[3px] border-l-accent-brain">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2 text-sm font-semibold text-accent-brain">
              <Brain size={15} />
              The Brain
            </div>
            <span className="w-2 h-2 rounded-full bg-status-done animate-brain-pulse" />
          </div>
          <div className="space-y-3">
            <div className="flex justify-between text-sm">
              <span className="text-text-tertiary">Status</span>
              <span className="text-text-primary font-medium">Online — monitoring</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-text-tertiary">Clusters</span>
              <span className="text-text-primary font-mono">{clusters.length}</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-text-tertiary">Open issues</span>
              <span className={cn("font-mono", issues.length > 0 ? "text-status-blocked" : "text-status-done")}>{issues.length}</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-text-tertiary">Active tasks</span>
              <span className="text-text-primary font-mono">{totalActive}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
