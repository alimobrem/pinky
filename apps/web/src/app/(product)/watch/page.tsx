"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { Brain, Eye, EyeOff, CheckCircle, Filter } from "lucide-react";
import { toast } from "sonner";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import type { Issue, PaginatedResponse } from "@pinky/contracts";
import { EmptyState } from "@/components/empty-state";
import { PageHeader } from "@/components/page-header";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from "@/components/ui/alert-dialog";
import { useSSE } from "@/hooks/use-sse";
import { api } from "@/lib/api";
import { useCluster } from "@/hooks/use-cluster";
import { relativeTime } from "@/lib/format-date";
import { SEVERITY_VARIANT, SEVERITY_BORDER } from "@/lib/status-colors";

export default function WatchPage() {
  const cluster = useCluster();
  const queryClient = useQueryClient();
  const [actingId, setActingId] = useState<string | null>(null);
  const [severityFilter, setSeverityFilter] = useState("all");
  const [confirmAction, setConfirmAction] = useState<{ id: string; action: "suppress" | "resolve"; title: string } | null>(null);

  const queryKey = ["issues", cluster] as const;
  const { data, isLoading, error: fetchError } = useQuery({
    queryKey,
    queryFn: () => {
      let url = "/api/v1/issues?status=open";
      if (cluster && cluster !== "all") url += `&cluster_id=${cluster}`;
      return api.get<PaginatedResponse<Issue>>(url);
    },
  });

  const allIssues = data?.items ?? [];
  const issues = severityFilter === "all"
    ? allIssues
    : allIssues.filter(i => i.severity === severityFilter);

  const sseHandlers = useMemo(() => ({
    update: () => queryClient.invalidateQueries({ queryKey: ["issues"] }),
  }), [queryClient]);

  const { state: sseState, lastUpdated } = useSSE("/api/v1/streams/watch", { onEvent: sseHandlers });
  const connected = sseState === "connected";

  const suppressMutation = useMutation({
    mutationFn: (id: string) => { setActingId(id); return api.post(`/api/v1/issues/${id}/suppress`, {}); },
    onSuccess: () => { toast.success("Issue suppressed"); queryClient.invalidateQueries({ queryKey: ["issues"] }); },
    onError: (e: Error) => toast.error(e.message),
    onSettled: () => setActingId(null),
  });

  const resolveMutation = useMutation({
    mutationFn: (id: string) => { setActingId(id); return api.post(`/api/v1/issues/${id}/resolve`); },
    onSuccess: () => { toast.success("Issue resolved"); queryClient.invalidateQueries({ queryKey: ["issues"] }); },
    onError: (e: Error) => toast.error(e.message),
    onSettled: () => setActingId(null),
  });

  const handleConfirm = () => {
    if (!confirmAction) return;
    if (confirmAction.action === "suppress") suppressMutation.mutate(confirmAction.id);
    else resolveMutation.mutate(confirmAction.id);
    setConfirmAction(null);
  };

  return (
    <div className="animate-fade-in">
      <PageHeader
        eyebrow="Live watch"
        title="Watch"
        description="A high-signal stream of issues The Brain thinks deserve attention right now."
        meta={
          <>
            <span className={`inline-block h-2 w-2 rounded-full ${connected ? "bg-status-done animate-brain-pulse" : "bg-status-blocked"}`} />
            <span>
              {connected
                ? `Live — updated ${lastUpdated ? relativeTime(lastUpdated.toISOString()) : "just now"}`
                : sseState === "reconnecting"
                  ? "Reconnecting..."
                  : "Connecting..."}
            </span>
          </>
        }
      />

      <div className="mt-6 flex flex-wrap items-center gap-3 rounded-2xl border border-border-default bg-bg-surface px-4 py-3 shadow-card">
        <Filter size={14} className="text-text-tertiary" />
        <Select value={severityFilter} onValueChange={setSeverityFilter}>
          <SelectTrigger className="w-[140px] h-8 text-xs" aria-label="Filter issues by severity">
            <SelectValue placeholder="All Severities" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Severities</SelectItem>
            <SelectItem value="critical">Critical</SelectItem>
            <SelectItem value="high">High</SelectItem>
            <SelectItem value="medium">Medium</SelectItem>
            <SelectItem value="low">Low</SelectItem>
          </SelectContent>
        </Select>
        <span className="ml-auto text-xs text-text-tertiary">{issues.length} of {allIssues.length} issues</span>
      </div>

      {fetchError && (
        <div className="mt-6 rounded-2xl border border-status-blocked/30 bg-status-blocked/10 px-4 py-3 text-sm text-status-blocked">{fetchError.message}</div>
      )}

      {isLoading && (
        <div className="mt-6 flex flex-col gap-3">
          {[1, 2, 3].map(i => <div key={i} className="skeleton h-28 rounded-2xl" />)}
        </div>
      )}

      {!isLoading && issues.length === 0 && !fetchError ? (
        <EmptyState
          className="mt-6"
          eyebrow="Everything is calm"
          icon={<Eye size={20} />}
          title="No active issues are bubbling up right now."
          description="The Brain is still monitoring your clusters. This view will fill as soon as live operational work needs triage."
          action={<Link href="/settings">Configure scanners →</Link>}
        />
      ) : issues.length > 0 ? (
        <div className="mt-6 flex flex-col gap-3">
          {issues.map(issue => (
            <div key={issue.id} className={`rounded-2xl border border-border-default border-l-[3px] bg-bg-surface p-5 shadow-card transition-all duration-200 hover:bg-bg-hover hover:shadow-card-hover ${SEVERITY_BORDER[issue.severity] || "border-l-border-default"}`}>
              <div className="flex justify-between items-center">
                <div className="flex items-center gap-2 flex-1">
                  <Brain size={14} className="text-accent-brain" />
                  <span className="font-semibold text-sm">{issue.title}</span>
                </div>
                <Badge variant={SEVERITY_VARIANT[issue.severity] || "outline"} className="uppercase text-xs">{issue.severity}</Badge>
              </div>
              <div className="text-xs text-text-tertiary mt-2 pl-6">
                {issue.status} — last seen {issue.last_seen_at ? relativeTime(issue.last_seen_at) : "unknown"}
              </div>
              <div className="flex gap-2 mt-3 pl-6">
                <Button variant="outline" size="sm" onClick={() => setConfirmAction({ id: issue.id, action: "suppress", title: issue.title })} disabled={actingId === issue.id} className="h-7 text-xs">
                  <EyeOff size={12} /> Suppress
                </Button>
                <Button variant="outline" size="sm" onClick={() => setConfirmAction({ id: issue.id, action: "resolve", title: issue.title })} disabled={actingId === issue.id} className="h-7 text-xs text-status-done">
                  <CheckCircle size={12} /> Resolve
                </Button>
                <Button variant="outline" size="sm" asChild className="h-7 text-xs">
                  <Link href={`/tasks?cluster=${issue.cluster_id}`}>View tasks</Link>
                </Button>
              </div>
            </div>
          ))}
        </div>
      ) : null}

      <AlertDialog open={!!confirmAction} onOpenChange={() => setConfirmAction(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>
              {confirmAction?.action === "suppress" ? "Suppress issue?" : "Resolve issue?"}
            </AlertDialogTitle>
            <AlertDialogDescription>
              {confirmAction?.action === "suppress"
                ? `This will suppress "${confirmAction?.title}". It won't trigger new tasks until it reappears after suppression expires.`
                : `This will mark "${confirmAction?.title}" as resolved. If the underlying problem persists, it will reopen automatically.`}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={handleConfirm}>
              {confirmAction?.action === "suppress" ? "Suppress" : "Resolve"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
