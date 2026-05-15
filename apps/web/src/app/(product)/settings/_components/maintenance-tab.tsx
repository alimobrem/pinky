"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { RefreshCw, AlertTriangle, CheckCircle2 } from "lucide-react";
import { toast } from "sonner";

interface WorkflowHealth {
  stuck_pending: number;
  stuck_running: number;
  stale_ready_tasks: number;
  orphaned_tasks: number;
  mismatched_task_issue: number;
}

interface ResetResult {
  stale_ready_expired: number;
  stuck_in_progress_reset: number;
  stuck_pending_failed: number;
  stuck_running_failed: number;
}

export function MaintenanceTab() {
  const qc = useQueryClient();

  const { data: health, isLoading } = useQuery({
    queryKey: ["workflow-health"],
    queryFn: () => api.get<WorkflowHealth>("/api/v1/health/workflows"),
    refetchInterval: 30_000,
  });

  const reset = useMutation({
    mutationFn: () => api.post<ResetResult>("/api/v1/admin/reset-stale"),
    onSuccess: (data) => {
      const total = Object.values(data).reduce((a, b) => a + b, 0);
      if (total === 0) {
        toast.info("Nothing to reset — all clean");
      } else {
        toast.success(`Reset ${total} stuck items`);
      }
      qc.invalidateQueries({ queryKey: ["workflow-health"] });
      qc.invalidateQueries({ queryKey: ["tasks"] });
    },
    onError: () => toast.error("Reset failed — check permissions"),
  });

  const totalIssues = health
    ? health.stuck_pending + health.stuck_running + health.stale_ready_tasks + health.orphaned_tasks + health.mismatched_task_issue
    : 0;

  return (
    <div className="space-y-4 pt-4">
      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium">Workflow Health</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {isLoading ? (
            <p className="text-caption text-text-tertiary">Loading...</p>
          ) : (
            <>
              <div className="grid grid-cols-2 gap-3">
                <HealthItem label="Stuck pending executions" value={health?.stuck_pending ?? 0} />
                <HealthItem label="Stuck running executions" value={health?.stuck_running ?? 0} />
                <HealthItem label="Stale ready tasks (>7d)" value={health?.stale_ready_tasks ?? 0} />
                <HealthItem label="Orphaned tasks" value={health?.orphaned_tasks ?? 0} />
                <HealthItem label="Done task / open issue mismatch" value={health?.mismatched_task_issue ?? 0} />
              </div>

              {totalIssues === 0 ? (
                <div className="flex items-center gap-2 rounded-lg bg-status-done/10 px-3 py-2 text-sm text-status-done">
                  <CheckCircle2 size={16} />
                  All workflows healthy
                </div>
              ) : (
                <div className="flex items-center gap-2 rounded-lg bg-status-in-progress/10 px-3 py-2 text-sm text-status-in-progress">
                  <AlertTriangle size={16} />
                  {totalIssues} item{totalIssues !== 1 ? "s" : ""} need attention
                </div>
              )}
            </>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium">Reset Stale Data</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <p className="text-caption text-text-secondary">
            Expires stale tasks (&gt;7 days), resets stuck in-progress tasks (&gt;24h),
            and fails orphaned executions. This is safe to run at any time.
          </p>
          <Button
            onClick={() => reset.mutate()}
            disabled={reset.isPending}
            variant="outline"
            className="gap-2"
          >
            <RefreshCw size={14} className={reset.isPending ? "animate-spin" : ""} />
            {reset.isPending ? "Resetting..." : "Reset Stale Items"}
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}

function HealthItem({ label, value }: { label: string; value: number }) {
  return (
    <div className="flex items-center justify-between rounded bg-bg-surface px-3 py-2">
      <span className="text-caption text-text-secondary">{label}</span>
      <span className={`font-mono text-sm tabular-nums ${value > 0 ? "text-status-in-progress" : "text-status-done"}`}>
        {value}
      </span>
    </div>
  );
}
