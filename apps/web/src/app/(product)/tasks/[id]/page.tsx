"use client";

import { useEffect, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import {
  ArrowLeft,
  Ban,
  Brain,
  CheckCircle,
  ChevronDown,
  ChevronRight,
  Link2,
  Play,
  Rocket,
  Shield,
  ShieldOff,
  UserPlus,
  Zap,
} from "lucide-react";
import { toast } from "sonner";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { Execution, Investigation, PaginatedResponse, TimelineEvent, WorkItem } from "@pinky/contracts";
import { ExecutionMonitor } from "@/components/execution-monitor";
import { PageHeader } from "@/components/page-header";
import { Badge } from "@/components/ui/badge";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { api } from "@/lib/api";
import { relativeTime, shortTime } from "@/lib/format-date";
import { cn } from "@/lib/utils";
import { confColor, confLabel } from "@/lib/status-colors";

const EVENT_ICONS: Record<string, string> = {
  started: "\u{1F680}",
  completed: "✅",
  failed: "❌",
  investigation_completed: "\u{1F50D}",
  verified: "✓",
};

export default function TaskDetailPage() {
  const params = useParams();
  const router = useRouter();
  const queryClient = useQueryClient();
  const taskId = params.id as string;

  const [showReasoning, setShowReasoning] = useState(false);
  const [blockOpen, setBlockOpen] = useState(false);
  const [blockReason, setBlockReason] = useState("");
  const [reassignOpen, setReassignOpen] = useState(false);
  const [reassignId, setReassignId] = useState("");
  const [rejectOpen, setRejectOpen] = useState(false);
  const [rejectReason, setRejectReason] = useState("");
  const [approveOpen, setApproveOpen] = useState(false);
  const [reinvestigateOpen, setReinvestigateOpen] = useState(false);
  const [ticketOpen, setTicketOpen] = useState(false);
  const [ticketUrl, setTicketUrl] = useState("");
  const [activeRemediationId, setActiveRemediationId] = useState<string | null>(null);
  const [investigating, setInvestigating] = useState(false);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const invalidateAll = () => {
    queryClient.invalidateQueries({ queryKey: ["work-item", taskId] });
    queryClient.invalidateQueries({ queryKey: ["investigation", taskId] });
    queryClient.invalidateQueries({ queryKey: ["timeline", taskId] });
    queryClient.invalidateQueries({ queryKey: ["active-executions", taskId] });
  };

  const { data: item, isLoading } = useQuery({
    queryKey: ["work-item", taskId],
    queryFn: () => api.get<WorkItem>(`/api/v1/work-items/${taskId}`),
  });

  const { data: investigation } = useQuery({
    queryKey: ["investigation", taskId],
    queryFn: () => api.get<Investigation>(`/api/v1/work-items/${taskId}/investigation`),
  });

  const { data: eventsData } = useQuery({
    queryKey: ["timeline", taskId],
    queryFn: () => api.get<{ items: TimelineEvent[] }>(`/api/v1/work-items/${taskId}/events`),
  });

  const { data: activeExecData } = useQuery({
    queryKey: ["active-executions", taskId],
    queryFn: () =>
      api.get<PaginatedResponse<Execution>>(
        `/api/v1/executions?work_item_id=${taskId}&status=pending,running,waiting_for_approval`,
      ),
    enabled: !!item,
  });

  const events = eventsData?.items ?? [];
  const inv = investigation?.has_investigation ? investigation : null;
  const executions = activeExecData?.items ?? [];
  const pendingExecution =
    executions.find((entry) => entry.execution_type === "remediation" && entry.status === "waiting_for_approval") ?? null;
  const runningRemediation =
    executions.find((entry) => entry.execution_type === "remediation" && (entry.status === "running" || entry.status === "pending")) ?? null;
  const activeInvestigation =
    executions.find((entry) => entry.execution_type === "investigation" && (entry.status === "pending" || entry.status === "running")) ?? null;
  const remediationPlanSteps = Array.isArray(item?.artifact_refs?.plan_steps) ? item.artifact_refs.plan_steps : [];
  const canStartRemediation = remediationPlanSteps.length > 0;

  const actionMutation = useMutation({
    mutationFn: (action: string) => api.post<WorkItem>(`/api/v1/work-items/${taskId}/${action}`),
    onSuccess: (_, action) => {
      toast.success(`Task ${action}ed`);
      invalidateAll();
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const blockMutation = useMutation({
    mutationFn: () => api.post<WorkItem>(`/api/v1/work-items/${taskId}/block`, { reason: blockReason }),
    onSuccess: () => {
      toast.success("Task blocked");
      setBlockOpen(false);
      setBlockReason("");
      invalidateAll();
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const reassignMutation = useMutation({
    mutationFn: () => api.post<WorkItem>(`/api/v1/work-items/${taskId}/reassign?assignee_id=${reassignId}`),
    onSuccess: () => {
      toast.success("Task reassigned");
      setReassignOpen(false);
      setReassignId("");
      invalidateAll();
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const approveMutation = useMutation({
    mutationFn: () => api.post(`/api/v1/executions/${pendingExecution!.id}/approve`, { changeset_digest: "approved" }),
    onSuccess: () => {
      toast.success("Approved");
      setApproveOpen(false);
      invalidateAll();
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const rejectMutation = useMutation({
    mutationFn: () => api.post(`/api/v1/executions/${pendingExecution!.id}/reject`, { reason: rejectReason }),
    onSuccess: () => {
      toast.success("Rejected");
      setRejectOpen(false);
      setRejectReason("");
      invalidateAll();
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const ticketMutation = useMutation({
    mutationFn: () => api.post(`/api/v1/work-items/${taskId}/annotations`, { annotations: { ticket_url: ticketUrl } }),
    onSuccess: () => {
      toast.success("Ticket linked");
      setTicketOpen(false);
      setTicketUrl("");
      invalidateAll();
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const triggerInvestigation = async () => {
    setInvestigating(true);
    try {
      if (activeInvestigation) {
        toast.warning("Investigation already in progress");
        setInvestigating(false);
        return;
      }
      await api.post(`/api/v1/executions?work_item_id=${taskId}&execution_type=investigation`);
      toast.info("Brain investigation started...");
      let attempts = 0;
      if (pollRef.current) clearInterval(pollRef.current);
      pollRef.current = setInterval(async () => {
        attempts++;
        try {
          const nextInvestigation = await api.get<Investigation>(`/api/v1/work-items/${taskId}/investigation`);
          if (nextInvestigation.has_investigation || attempts >= 10) {
            if (pollRef.current) clearInterval(pollRef.current);
            pollRef.current = null;
            setInvestigating(false);
            invalidateAll();
            if (nextInvestigation.has_investigation) toast.success("Investigation complete");
          }
        } catch {
          if (pollRef.current) clearInterval(pollRef.current);
          pollRef.current = null;
          setInvestigating(false);
        }
      }, 3000);
    } catch {
      toast.error("Network error");
      setInvestigating(false);
    }
  };

  const startRemediation = async () => {
    if (!canStartRemediation) {
      toast.error("No remediation plan is available for this task yet.");
      return;
    }
    try {
      const result = await api.post<{ id: string }>(`/api/v1/executions?work_item_id=${taskId}&execution_type=remediation`);
      setActiveRemediationId(result.id);
      toast.info("Remediation started");
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Failed");
    }
  };

  useEffect(() => () => {
    if (pollRef.current) clearInterval(pollRef.current);
  }, []);

  const acting =
    actionMutation.isPending || blockMutation.isPending || reassignMutation.isPending || investigating;

  useEffect(() => {
    if (!item || item.status === "done") return;
    const anyDialogOpen =
      blockOpen || reassignOpen || rejectOpen || approveOpen || reinvestigateOpen;
    const handler = (e: KeyboardEvent) => {
      if (
        e.target instanceof HTMLInputElement ||
        e.target instanceof HTMLTextAreaElement ||
        e.target instanceof HTMLSelectElement
      ) {
        return;
      }
      if (acting || anyDialogOpen) return;
      switch (e.key) {
        case "a":
          if (item.status === "ready") actionMutation.mutate("accept");
          break;
        case "s":
          if (item.status === "accepted" || item.status === "blocked") actionMutation.mutate("start");
          break;
        case "b":
          if (item.status === "in_progress") setBlockOpen(true);
          break;
        case "c":
          if (item.status === "in_progress") actionMutation.mutate("complete");
          break;
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [item, acting, blockOpen, reassignOpen, rejectOpen, approveOpen, reinvestigateOpen, actionMutation]);

  if (isLoading) {
    return (
      <div className="flex flex-col gap-4">
        {[1, 2, 3].map((i) => (
          <div key={i} className={`skeleton rounded-2xl ${i === 1 ? "h-[96px]" : "h-[220px]"}`} />
        ))}
      </div>
    );
  }

  if (!item) return <div className="py-16 text-center text-text-tertiary">Task not found.</div>;

  const isDone = item.status === "done";
  const headerActions = (
    <>
      {item.status === "ready" ? (
        <Button size="sm" onClick={() => actionMutation.mutate("accept")} disabled={acting}>
          Accept
        </Button>
      ) : null}
      {(item.status === "accepted" || item.status === "blocked") ? (
        <Button size="sm" onClick={() => actionMutation.mutate("start")} disabled={acting}>
          <Play size={13} />
          Start
        </Button>
      ) : null}
      {item.status === "in_progress" ? (
        <>
          <Button size="sm" variant="destructive" onClick={() => setBlockOpen(true)} disabled={acting}>
            <Ban size={13} />
            Block
          </Button>
          <Button size="sm" variant="secondary" onClick={() => actionMutation.mutate("complete")} disabled={acting}>
            <CheckCircle size={13} />
            Complete
          </Button>
        </>
      ) : null}
      {item.status === "waiting_for_approval" && pendingExecution ? (
        <>
          <Button size="sm" onClick={() => setApproveOpen(true)} disabled={acting}>
            <Shield size={13} />
            Approve
          </Button>
          <Button size="sm" variant="destructive" onClick={() => setRejectOpen(true)} disabled={acting}>
            <ShieldOff size={13} />
            Reject
          </Button>
        </>
      ) : null}
      {!isDone ? (
        <Button size="sm" variant="outline" onClick={() => setReassignOpen(true)} disabled={acting}>
          <UserPlus size={13} />
        </Button>
      ) : null}
      {!isDone ? (
        <Button size="sm" variant="outline" onClick={() => setTicketOpen(true)}>
          <Link2 size={13} />
        </Button>
      ) : null}
    </>
  );

  return (
    <div className="space-y-6">
      <div className="mb-1">
        <button
          onClick={() => router.push("/tasks")}
          className="flex cursor-pointer items-center gap-2 border-none bg-transparent text-sm text-text-secondary hover:text-text-primary"
        >
          <ArrowLeft size={16} /> Back to Tasks
        </button>
      </div>

      <PageHeader
        eyebrow="Investigation workspace"
        title={item.title}
        description={
          item.why_now ||
          item.recommended_next_step ||
          "Use this workspace to review the investigation, decide on next actions, and keep execution state visible."
        }
        meta={
          <>
            <Badge variant="outline">{item.status.replace(/_/g, " ")}</Badge>
            <Badge variant="outline">{item.priority}</Badge>
            {item.confidence != null ? (
              <span className={cn("font-mono tabular", confColor(item.confidence))}>
                {Math.round(item.confidence * 100)}% confidence
              </span>
            ) : null}
            <span>Created {relativeTime(item.created_at)}</span>
          </>
        }
        actions={headerActions}
      />

      <div className="flex flex-wrap gap-2">
        {Object.entries(item.labels).map(([k, v]) => (
          <span
            key={k}
            className="rounded-full border border-border-subtle bg-bg-elevated px-2 py-1 text-[11px] text-text-secondary"
          >
            {k}={v}
          </span>
        ))}
        {item.annotations?.ticket_url ? (
          <a
            href={item.annotations.ticket_url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1 rounded-full border border-border-subtle bg-bg-elevated px-2 py-1 text-[11px] text-accent-brand no-underline"
          >
            <Link2 size={12} /> {item.annotations.ticket_url.replace(/^https?:\/\//, "").slice(0, 40)}
          </a>
        ) : null}
      </div>

      {item.status === "blocked" && item.blocked_reason ? (
        <div className="rounded-xl border border-status-blocked/30 bg-status-blocked/10 px-4 py-3 text-sm font-medium text-status-blocked">
          <div className="flex items-center gap-2">
            <Ban size={14} />
            <span>Blocked: {item.blocked_reason}</span>
          </div>
        </div>
      ) : null}

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-[minmax(0,1fr)_360px]">
        <div className="space-y-4">
          <section className="rounded-2xl border border-border-default bg-bg-surface p-5 shadow-card">
            <h2 className="mb-3 border-b border-border-subtle pb-2 text-xs font-semibold uppercase tracking-[0.16em] text-text-tertiary">
              Situation summary
            </h2>
            <div className="space-y-4">
              <div>
                <div className="mb-1 text-xs font-semibold uppercase tracking-[0.16em] text-text-tertiary">
                  Why now
                </div>
                <div className="text-sm leading-relaxed text-text-secondary">
                  {item.why_now || "No short narrative has been attached to this task yet."}
                </div>
              </div>
              <div className="grid gap-3 sm:grid-cols-2">
                <div className="rounded-xl border border-border-subtle bg-bg-elevated/80 px-3 py-3">
                  <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-text-tertiary">
                    Status
                  </div>
                  <div className="mt-2 text-sm font-semibold text-text-primary">
                    {item.status.replace(/_/g, " ")}
                  </div>
                </div>
                <div className="rounded-xl border border-border-subtle bg-bg-elevated/80 px-3 py-3">
                  <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-text-tertiary">
                    Priority
                  </div>
                  <div className="mt-2 text-sm font-semibold text-text-primary">
                    {item.priority}
                  </div>
                </div>
              </div>
            </div>
          </section>

          {inv ? (
            <section className="rounded-2xl border border-border-default bg-bg-surface p-5 shadow-card">
              <h2 className="mb-3 flex items-center gap-2 border-b border-border-subtle pb-2 text-xs font-semibold uppercase tracking-[0.16em] text-text-tertiary">
                <Brain size={14} className="text-accent-brain" /> Investigation
              </h2>
              <div className="space-y-4">
                {inv.summary ? (
                  <div className="whitespace-pre-wrap text-sm leading-relaxed text-text-primary">
                    {inv.summary}
                  </div>
                ) : null}
                {inv.root_cause && inv.root_cause !== inv.summary ? (
                  <div>
                    <button
                      onClick={() => setShowReasoning(!showReasoning)}
                      className="mt-1 flex cursor-pointer items-center gap-2 border-none bg-transparent text-sm font-semibold text-accent-brain"
                    >
                      {showReasoning ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                      View full analysis
                    </button>
                    {showReasoning ? (
                      <div className="mt-3 whitespace-pre-wrap border-t border-border-brain pt-3 text-sm leading-relaxed text-text-secondary">
                        {inv.root_cause}
                      </div>
                    ) : null}
                  </div>
                ) : null}
                <div className="text-xs font-semibold text-text-tertiary">
                  Investigated {inv.created_at ? relativeTime(inv.created_at) : "recently"}
                </div>
              </div>
            </section>
          ) : (
            <section className="rounded-2xl border border-border-default bg-bg-surface p-5 text-center shadow-card">
              <Brain size={24} className="mx-auto mb-3 text-text-tertiary" />
              <p className="mb-2 text-text-secondary">No investigation data yet.</p>
              <p className="text-sm text-text-tertiary">
                Trigger an investigation to have The Brain analyze this issue.
              </p>
            </section>
          )}

          <section className="rounded-2xl border border-border-default bg-bg-surface p-5 shadow-card">
            <h2 className="mb-3 border-b border-border-subtle pb-2 text-xs font-semibold uppercase tracking-[0.16em] text-text-tertiary">
              Execution timeline
            </h2>
            {events.length === 0 ? (
              <p className="py-4 text-sm text-text-tertiary">No execution events yet.</p>
            ) : (
              <div className="space-y-1">
                {events.map((event) => (
                  <div key={event.id} className="grid grid-cols-[24px_84px_1fr] gap-3 py-3 [&+&]:border-t [&+&]:border-border-subtle">
                    <div className="flex justify-center pt-1">
                      <div
                        className={cn(
                          "h-2.5 w-2.5 rounded-full",
                          event.event_type.includes("failed")
                            ? "bg-status-blocked"
                            : event.event_type.includes("completed") || event.event_type.includes("verified")
                              ? "bg-status-done"
                              : "bg-accent-brain",
                        )}
                      />
                    </div>
                    <span className="font-mono text-[11px] text-text-tertiary tabular">
                      {shortTime(event.occurred_at)}
                    </span>
                    <div className="min-w-0">
                      <Link
                        href={`/tasks/${taskId}/execution/${event.execution_id}`}
                        className="text-sm font-medium text-text-primary no-underline hover:text-accent-brand"
                      >
                        {EVENT_ICONS[event.event_type] || "•"} {event.event_type.replace(/_/g, " ")}
                      </Link>
                      {event.payload && Object.keys(event.payload).length > 0 ? (
                        <div className="mt-1 text-xs text-text-tertiary">
                          {Object.entries(event.payload)
                            .slice(0, 3)
                            .map(([k, v]) => (
                              <span key={k} className="mr-3">
                                {k}: {String(v)}
                              </span>
                            ))}
                        </div>
                      ) : null}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </section>
        </div>

        <div className="space-y-4">
          <div className="rounded-2xl border border-border-brain border-l-[3px] border-l-accent-brain bg-[var(--accent-brain-bg)] p-5 shadow-brain-glow">
            <div className="mb-3 flex items-center justify-between">
              <div className="flex items-center gap-2 text-sm font-semibold text-accent-brain">
                <Brain size={16} /> The Brain recommends
              </div>
              {(inv?.confidence ?? item.confidence) != null ? (
                <div className="text-right">
                  <div className={cn("font-mono text-lg font-bold tabular", confColor((inv?.confidence ?? item.confidence)!))}>
                    {Math.round((inv?.confidence ?? item.confidence)! * 100)}%
                  </div>
                  <div className="text-[11px] text-text-tertiary">
                    {confLabel((inv?.confidence ?? item.confidence)!)}
                  </div>
                </div>
              ) : null}
            </div>
            <div className="text-sm leading-relaxed text-text-primary">
              {inv?.recommended_action || item.recommended_next_step || "No recommendation available yet."}
            </div>
            {item.runbook_url ? (
              <div className="mt-3 border-t border-border-brain pt-3">
                <a
                  href={item.runbook_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-sm text-accent-brain"
                >
                  View runbook
                </a>
              </div>
            ) : null}
          </div>

          <div className="rounded-2xl border border-border-default bg-bg-surface p-4 shadow-card">
            <div className="mb-3 text-[11px] font-semibold uppercase tracking-[0.18em] text-text-tertiary">
              Next moves
            </div>
            <div className="space-y-2">
              {inv ? (
                <Button variant="outline" className="w-full border-border-brain text-accent-brain hover:bg-accent-brain/10" onClick={() => setReinvestigateOpen(true)} disabled={acting}>
                  <Zap size={16} /> {investigating ? "Brain is investigating..." : "Re-investigate"}
                </Button>
              ) : (
                <Button variant="outline" className="w-full border-border-brain text-accent-brain hover:bg-accent-brain/10" onClick={triggerInvestigation} disabled={acting}>
                  <Zap size={16} /> {investigating ? "Brain is investigating..." : "Run Brain Investigation"}
                </Button>
              )}

              {inv?.recommended_action && !activeRemediationId && !runningRemediation && !pendingExecution && !isDone && canStartRemediation ? (
                <Button variant="outline" className="w-full border-accent-brand-dim text-accent-brand hover:bg-accent-brand/10" onClick={startRemediation} disabled={acting}>
                  <Rocket size={16} /> Start Remediation
                </Button>
              ) : null}
            </div>
          </div>

          {(activeRemediationId || runningRemediation?.id || pendingExecution?.id) ? (
            <div className="rounded-2xl border border-border-default bg-bg-surface p-4 shadow-card">
              <div className="mb-2 text-xs font-semibold uppercase tracking-[0.16em] text-text-tertiary">
                Live execution
              </div>
              <ExecutionMonitor
                executionId={activeRemediationId || runningRemediation?.id || pendingExecution!.id}
                onComplete={invalidateAll}
              />
              <Link
                href={`/tasks/${taskId}/execution/${activeRemediationId || runningRemediation?.id || pendingExecution!.id}`}
                className="mt-2 block text-xs text-accent-brand"
              >
                View full execution detail
              </Link>
            </div>
          ) : null}
        </div>
      </div>

      <Dialog open={blockOpen} onOpenChange={(open) => { if (!open) { setBlockOpen(false); setBlockReason(""); } }}>
        <DialogContent>
          <DialogHeader><DialogTitle>Mark as Blocked</DialogTitle></DialogHeader>
          <div className="space-y-2">
            <Label>Reason *</Label>
            <Textarea value={blockReason} onChange={(e) => setBlockReason(e.target.value)} placeholder="Why is this task blocked?" rows={3} />
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => { setBlockOpen(false); setBlockReason(""); }}>Cancel</Button>
            <Button variant="destructive" onClick={() => blockMutation.mutate()} disabled={!blockReason.trim()}>Block Task</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={reassignOpen} onOpenChange={(open) => { if (!open) { setReassignOpen(false); setReassignId(""); } }}>
        <DialogContent>
          <DialogHeader><DialogTitle>Reassign Task</DialogTitle></DialogHeader>
          <div className="space-y-2">
            <Label>Assignee ID *</Label>
            <Input value={reassignId} onChange={(e) => setReassignId(e.target.value)} placeholder="UUID of the new assignee" />
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => { setReassignOpen(false); setReassignId(""); }}>Cancel</Button>
            <Button onClick={() => reassignMutation.mutate()} disabled={!reassignId.trim()}>Reassign</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <AlertDialog open={approveOpen} onOpenChange={setApproveOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Approve Execution</AlertDialogTitle>
            <AlertDialogDescription>This will allow The Brain to proceed with the recommended remediation.</AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={() => approveMutation.mutate()}>Approve</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      <Dialog open={rejectOpen} onOpenChange={(open) => { if (!open) { setRejectOpen(false); setRejectReason(""); } }}>
        <DialogContent>
          <DialogHeader><DialogTitle>Reject Execution</DialogTitle></DialogHeader>
          <div className="space-y-2">
            <Label>Reason *</Label>
            <Textarea value={rejectReason} onChange={(e) => setRejectReason(e.target.value)} placeholder="Why are you rejecting?" rows={3} />
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => { setRejectOpen(false); setRejectReason(""); }}>Cancel</Button>
            <Button variant="destructive" onClick={() => rejectMutation.mutate()} disabled={!rejectReason.trim()}>Reject</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <AlertDialog open={reinvestigateOpen} onOpenChange={setReinvestigateOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Re-investigate</AlertDialogTitle>
            <AlertDialogDescription>This will start a new investigation, overwriting cached results.</AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={() => { setReinvestigateOpen(false); triggerInvestigation(); }}>Re-investigate</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      <Dialog open={ticketOpen} onOpenChange={(open) => { if (!open) { setTicketOpen(false); setTicketUrl(""); } }}>
        <DialogContent>
          <DialogHeader><DialogTitle>Link External Ticket</DialogTitle></DialogHeader>
          <div className="space-y-2">
            <Label>Ticket URL *</Label>
            <Input value={ticketUrl} onChange={(e) => setTicketUrl(e.target.value)} placeholder="https://jira.example.com/browse/OPS-123" />
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => { setTicketOpen(false); setTicketUrl(""); }}>Cancel</Button>
            <Button onClick={() => ticketMutation.mutate()} disabled={!ticketUrl.trim()}>Link</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
