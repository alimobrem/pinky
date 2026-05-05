"use client";

import { useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  ArrowLeft,
  Play,
  CheckCircle2,
  Ban,
  UserPlus,
  Brain,
  ExternalLink,
  ChevronRight,
  Loader2,
  Search,
  XCircle,
  RotateCcw,
  AlertTriangle,
  CheckCircle,
} from "lucide-react";

import { api } from "@/lib/api";
import { QUERY_KEYS } from "@/lib/constants";
import {
  taskOptions,
  investigationOptions,
  timelineOptions,
  executionsOptions,
} from "../queries";
import { useSSE } from "@/hooks/use-sse";
import { StatusIndicator } from "@/components/shared/status-indicator";
import { PriorityBadge } from "@/components/shared/priority-badge";
import { ConfidenceBadge } from "@/components/shared/confidence-badge";
import { RelativeTime } from "@/components/shared/relative-time";
import { ApprovalGate } from "@/components/shared/approval-gate";
import { PageHeader } from "@/components/shared/page-header";
import { FadeIn } from "@/components/motion/fade-in";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { useState, useEffect, useMemo, useCallback } from "react";
import { toast } from "sonner";
import type { Execution } from "@pinky/contracts";

type InvestigationState =
  | "idle"
  | "starting"
  | "gathering_evidence"
  | "analyzing"
  | "completed"
  | "failed"
  | "timed_out";

interface TaskDetailViewProps {
  taskId: string;
}

export function TaskDetailView({ taskId }: TaskDetailViewProps) {
  const router = useRouter();
  const qc = useQueryClient();
  const [blockReason, setBlockReason] = useState("");
  const [reassignId, setReassignId] = useState("");
  const [investigationState, setInvestigationState] = useState<InvestigationState>("idle");
  const [activeExecId, setActiveExecId] = useState<string | null>(null);

  const { data: task } = useQuery(taskOptions(taskId));
  const { data: investigation } = useQuery(investigationOptions(taskId));
  const { data: timeline } = useQuery(timelineOptions(taskId));
  const { data: executions } = useQuery(executionsOptions(taskId));

  const invalidate = () => {
    qc.invalidateQueries({ queryKey: QUERY_KEYS.task(taskId) });
    qc.invalidateQueries({ queryKey: QUERY_KEYS.tasks() });
  };

  const invalidateInvestigation = useCallback(() => {
    qc.invalidateQueries({ queryKey: QUERY_KEYS.taskInvestigation(taskId) });
    qc.invalidateQueries({ queryKey: QUERY_KEYS.taskTimeline(taskId) });
    qc.invalidateQueries({ queryKey: [...QUERY_KEYS.executions(), taskId] });
  }, [qc, taskId]);

  // Detect active investigation on page load / data change
  useEffect(() => {
    if (!executions?.items || investigationState === "starting") return;

    const runningExec = executions.items.find(
      (e) =>
        (e.status === "running" || e.status === "pending") &&
        e.execution_type === "investigation",
    );

    if (runningExec) {
      const startedAt = new Date(runningExec.started_at ?? runningExec.created_at);
      const elapsed = Date.now() - startedAt.getTime();
      const STUCK_THRESHOLD_MS = 5 * 60 * 1000;

      if (elapsed > STUCK_THRESHOLD_MS) {
        setInvestigationState("timed_out");
      } else if (investigationState === "idle") {
        setInvestigationState("analyzing");
      }
      setActiveExecId(runningExec.id);
    }
  }, [executions, investigationState]);

  // SSE subscription for execution progress
  const sseEventHandlers = useMemo(
    () => ({
      update: (raw: string) => {
        try {
          const data = JSON.parse(raw) as { type?: string; payload?: Record<string, unknown> };
          const eventType = data.payload?.event_type ?? data.type;

          if (eventType === "execution.started" || eventType === "started") {
            setInvestigationState("gathering_evidence");
          } else if (eventType === "execution.progress" || eventType === "progress" || eventType === "tool_used") {
            setInvestigationState("analyzing");
          } else if (eventType === "execution.completed" || eventType === "completed" || eventType === "investigation_completed") {
            setInvestigationState("completed");
            invalidateInvestigation();
          } else if (eventType === "execution.failed" || eventType === "failed") {
            setInvestigationState("failed");
            invalidateInvestigation();
          } else if (eventType === "execution.timed_out" || eventType === "timed_out") {
            setInvestigationState("timed_out");
            invalidateInvestigation();
          } else if (eventType === "execution.cancelled") {
            setInvestigationState("idle");
            setActiveExecId(null);
            invalidateInvestigation();
          }

          // Always refresh timeline on any event
          qc.invalidateQueries({ queryKey: QUERY_KEYS.taskTimeline(taskId) });
        } catch {
          // Non-JSON payloads are ignored
        }
      },
    }),
    [invalidateInvestigation, qc, taskId],
  );

  useSSE(
    activeExecId
      ? `/api/v1/streams/executions/${activeExecId}`
      : "/api/v1/streams/executions/__noop__",
    {
      onEvent: sseEventHandlers,
      enabled: !!activeExecId && investigationState !== "idle" && investigationState !== "completed",
    },
  );

  const accept = useMutation({
    mutationFn: () => api.post(`/api/v1/work-items/${taskId}/accept`),
    onSuccess: () => { invalidate(); toast.success("Task accepted"); },
  });
  const start = useMutation({
    mutationFn: () => api.post(`/api/v1/work-items/${taskId}/start`),
    onSuccess: () => { invalidate(); toast.success("Task started"); },
  });
  const complete = useMutation({
    mutationFn: () => api.post(`/api/v1/work-items/${taskId}/complete`),
    onSuccess: () => { invalidate(); toast.success("Task completed"); },
  });
  const block = useMutation({
    mutationFn: (reason: string) =>
      api.post(`/api/v1/work-items/${taskId}/block`, { reason }),
    onSuccess: () => { invalidate(); setBlockReason(""); toast.success("Task blocked"); },
  });
  const reassign = useMutation({
    mutationFn: (assigneeId: string) =>
      api.post(`/api/v1/work-items/${taskId}/reassign?assignee_id=${assigneeId}`),
    onSuccess: () => { invalidate(); setReassignId(""); toast.success("Task reassigned"); },
  });
  const approve = useMutation({
    mutationFn: (execId: string) => api.post(`/api/v1/executions/${execId}/approve`),
    onSuccess: () => { invalidate(); toast.success("Execution approved"); },
  });
  const reject = useMutation({
    mutationFn: (execId: string) => api.post(`/api/v1/executions/${execId}/reject`),
    onSuccess: () => { invalidate(); toast.success("Execution rejected"); },
  });
  const investigate = useMutation({
    mutationFn: () =>
      api.post<Execution>(
        `/api/v1/executions?work_item_id=${encodeURIComponent(taskId)}&execution_type=investigation`,
      ),
    onSuccess: (result) => {
      setActiveExecId(result.id);
      setInvestigationState("gathering_evidence");
      invalidate();
      toast.success("Investigation started — The Brain is analyzing the issue");
    },
    onError: () => {
      setInvestigationState("idle");
      toast.error("Failed to start investigation");
    },
  });

  const handleStartInvestigation = () => {
    setInvestigationState("starting");
    investigate.mutate();
  };

  const handleCancelInvestigation = async () => {
    if (!activeExecId) return;
    try {
      await api.post(`/api/v1/executions/${activeExecId}/cancel`);
      setInvestigationState("idle");
      setActiveExecId(null);
      invalidateInvestigation();
      toast.info("Investigation cancelled");
    } catch {
      toast.error("Failed to cancel investigation");
    }
  };

  if (!task) return null;

  const pendingExec = executions?.items?.find(
    (e) => e.status === "waiting_for_approval",
  );
  const activeExec = executions?.items?.find(
    (e) => e.status === "running" || e.status === "pending",
  );
  const events = timeline?.items ?? [];
  const isInvestigationInProgress =
    investigationState === "starting" ||
    investigationState === "gathering_evidence" ||
    investigationState === "analyzing";

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Button
          variant="ghost"
          size="icon"
          className="h-8 w-8"
          onClick={() => router.back()}
        >
          <ArrowLeft size={16} />
        </Button>
        <PageHeader
          title={task.title}
          meta={
            <>
              <StatusIndicator status={task.status} />
              <PriorityBadge priority={task.priority} />
              <ConfidenceBadge value={task.confidence} />
              <RelativeTime date={task.created_at} />
            </>
          }
          className="mb-0 flex-1"
        />
      </div>

      <FadeIn>
        <div className="grid gap-4 lg:grid-cols-3">
          <div className="space-y-4 lg:col-span-2">
            {task.why_now && (
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-caption font-semibold uppercase tracking-widest text-text-tertiary">
                    Situation
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-sm leading-relaxed text-text-secondary">
                    {task.why_now}
                  </p>
                </CardContent>
              </Card>
            )}

            {isInvestigationInProgress && (
              <InvestigationProgress state={investigationState} />
            )}

            {investigationState === "failed" && (
              <Card className="border-red-500/20 bg-red-500/5">
                <CardContent className="flex items-center gap-3 p-4">
                  <AlertTriangle className="h-4 w-4 shrink-0 text-red-400" />
                  <span className="flex-1 text-sm text-red-300">
                    Investigation failed. You can retry.
                  </span>
                  <Button
                    size="sm"
                    variant="destructive"
                    className="gap-2"
                    onClick={handleStartInvestigation}
                  >
                    <RotateCcw size={14} />
                    Retry
                  </Button>
                </CardContent>
              </Card>
            )}

            {investigationState === "timed_out" && (
              <Card className="border-amber-500/20 bg-amber-500/5">
                <CardContent className="flex items-center gap-3 p-4">
                  <AlertTriangle className="h-4 w-4 shrink-0 text-amber-400" />
                  <span className="flex-1 text-sm text-amber-300">
                    Investigation appears stuck (running over 5 minutes).
                  </span>
                  <Button
                    size="sm"
                    variant="outline"
                    className="gap-2 text-amber-400 border-amber-500/30"
                    onClick={handleCancelInvestigation}
                  >
                    <XCircle size={14} />
                    Cancel
                  </Button>
                </CardContent>
              </Card>
            )}

            {investigation?.has_investigation &&
              investigation.recommended_action && (
                <Card className="border-purple-500/20 bg-purple-500/5">
                  <CardContent className="p-4">
                    <div className="flex items-center gap-2 mb-2">
                      <Brain className="h-4 w-4 text-purple-400" />
                      <span className="text-sm font-medium text-purple-300">
                        The Brain recommends
                      </span>
                      {investigation.confidence != null && (
                        <ConfidenceBadge value={investigation.confidence} />
                      )}
                    </div>
                    <p className="text-sm text-text-primary">
                      {investigation.recommended_action}
                    </p>

                    <Collapsible>
                      <CollapsibleTrigger className="flex items-center gap-1 mt-3 text-xs text-text-secondary hover:text-text-primary">
                        <ChevronRight className="h-3 w-3" />
                        View reasoning
                      </CollapsibleTrigger>
                      <CollapsibleContent className="mt-2 space-y-2">
                        {investigation.summary && (
                          <div>
                            <span className="text-xs font-medium text-text-secondary">
                              Summary
                            </span>
                            <p className="text-sm text-text-primary">
                              {investigation.summary}
                            </p>
                          </div>
                        )}
                        {investigation.root_cause && (
                          <div>
                            <span className="text-xs font-medium text-text-secondary">
                              Root cause
                            </span>
                            <p className="text-sm text-text-primary">
                              {investigation.root_cause}
                            </p>
                          </div>
                        )}
                      </CollapsibleContent>
                    </Collapsible>

                    {investigation.tool_calls &&
                      investigation.tool_calls.length > 0 && (
                        <div className="flex flex-wrap gap-1.5 mt-3 pt-3 border-t border-border-default">
                          <span className="text-xs text-text-secondary">
                            Tools:
                          </span>
                          {investigation.tool_calls.map((tool) => (
                            <Badge
                              key={tool}
                              variant="outline"
                              className="text-xs font-mono"
                            >
                              {tool}
                            </Badge>
                          ))}
                        </div>
                      )}
                  </CardContent>
                </Card>
              )}

            {events.length > 0 && (
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-caption font-semibold uppercase tracking-widest text-text-tertiary">
                    Timeline
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    {events.map((event) => (
                      <div
                        key={event.id}
                        className="flex items-center gap-3 rounded-md px-2 py-1.5 text-sm hover:bg-bg-hover"
                      >
                        <span className="w-2 h-2 rounded-full bg-brand-purple shrink-0" />
                        <span className="flex-1 text-text-secondary">
                          {event.event_type.replace(/_/g, " ")}
                        </span>
                        <RelativeTime date={event.occurred_at} />
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}

            {pendingExec && (
              <ApprovalGate
                executionId={pendingExec.id}
                onApprove={(id) => approve.mutate(id)}
                onReject={(id) => reject.mutate(id)}
                isPending={approve.isPending || reject.isPending}
              />
            )}
          </div>

          <div className="space-y-4">
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-caption font-semibold uppercase tracking-widest text-text-tertiary">
                  Actions
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                {task.status === "ready" && (
                  <Button
                    size="sm"
                    className="w-full justify-start gap-2"
                    onClick={() => accept.mutate()}
                    disabled={accept.isPending}
                  >
                    <CheckCircle2 size={14} />
                    Accept
                  </Button>
                )}
                {(task.status === "accepted" || task.status === "blocked") && (
                  <Button
                    size="sm"
                    className="w-full justify-start gap-2"
                    onClick={() => start.mutate()}
                    disabled={start.isPending}
                  >
                    <Play size={14} />
                    Start
                  </Button>
                )}
                {task.status === "in_progress" && (
                  <>
                    <Button
                      size="sm"
                      className="w-full justify-start gap-2 bg-status-done text-text-inverse hover:bg-status-done/90"
                      onClick={() => complete.mutate()}
                      disabled={complete.isPending}
                    >
                      <CheckCircle2 size={14} />
                      Complete
                    </Button>
                    <Dialog>
                      <DialogTrigger asChild>
                        <Button
                          size="sm"
                          variant="outline"
                          className="w-full justify-start gap-2 border-status-blocked/30 text-status-blocked"
                        >
                          <Ban size={14} />
                          Block
                        </Button>
                      </DialogTrigger>
                      <DialogContent>
                        <DialogHeader>
                          <DialogTitle>Block reason</DialogTitle>
                        </DialogHeader>
                        <Textarea
                          value={blockReason}
                          onChange={(e) => setBlockReason(e.target.value)}
                          placeholder="Why is this task blocked?"
                          className="min-h-[80px]"
                        />
                        <Button
                          onClick={() => block.mutate(blockReason)}
                          disabled={!blockReason || block.isPending}
                        >
                          Block task
                        </Button>
                      </DialogContent>
                    </Dialog>
                  </>
                )}

                {investigationState === "idle" &&
                  !activeExec && (
                    <Button
                      size="sm"
                      variant="outline"
                      className="w-full justify-start gap-2"
                      onClick={handleStartInvestigation}
                    >
                      <Brain size={14} className="text-brand-purple" />
                      Start Investigation
                    </Button>
                  )}
                {investigationState === "starting" && (
                  <Button
                    size="sm"
                    variant="outline"
                    className="w-full justify-start gap-2"
                    disabled
                  >
                    <Loader2 size={14} className="animate-spin" />
                    Starting...
                  </Button>
                )}
                {(investigationState === "gathering_evidence" ||
                  investigationState === "analyzing") && (
                  <Button
                    size="sm"
                    variant="outline"
                    className="w-full justify-start gap-2 border-amber-500/30 text-amber-400"
                    onClick={handleCancelInvestigation}
                  >
                    <XCircle size={14} />
                    Cancel Investigation
                  </Button>
                )}
                {investigationState === "failed" && (
                  <Button
                    size="sm"
                    variant="outline"
                    className="w-full justify-start gap-2 border-red-500/30 text-red-400"
                    onClick={handleStartInvestigation}
                  >
                    <RotateCcw size={14} />
                    Retry Investigation
                  </Button>
                )}
                {investigationState === "timed_out" && (
                  <Button
                    size="sm"
                    variant="outline"
                    className="w-full justify-start gap-2 border-amber-500/30 text-amber-400"
                    onClick={handleCancelInvestigation}
                  >
                    <XCircle size={14} />
                    Cancel Stuck Investigation
                  </Button>
                )}

                <Dialog>
                  <DialogTrigger asChild>
                    <Button
                      size="sm"
                      variant="ghost"
                      className="w-full justify-start gap-2 text-text-secondary"
                    >
                      <UserPlus size={14} />
                      Reassign
                    </Button>
                  </DialogTrigger>
                  <DialogContent>
                    <DialogHeader>
                      <DialogTitle>Reassign task</DialogTitle>
                    </DialogHeader>
                    <Input
                      value={reassignId}
                      onChange={(e) => setReassignId(e.target.value)}
                      placeholder="Assignee"
                    />
                    <Button
                      onClick={() => reassign.mutate(reassignId)}
                      disabled={!reassignId || reassign.isPending}
                    >
                      Reassign
                    </Button>
                  </DialogContent>
                </Dialog>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-caption font-semibold uppercase tracking-widest text-text-tertiary">
                  Details
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-2 text-sm">
                <DetailRow label="Status">
                  <StatusIndicator status={task.status} />
                </DetailRow>
                <DetailRow label="Priority">
                  <PriorityBadge priority={task.priority} />
                </DetailRow>
                <DetailRow label="Confidence">
                  <ConfidenceBadge value={task.confidence} />
                </DetailRow>
                <DetailRow label="Created">
                  <RelativeTime date={task.created_at} />
                </DetailRow>
                <DetailRow label="Updated">
                  <RelativeTime date={task.updated_at} />
                </DetailRow>
                {task.blocked_reason && (
                  <DetailRow label="Blocked">
                    <span className="text-status-blocked">{task.blocked_reason}</span>
                  </DetailRow>
                )}
                {task.issue_id && (
                  <DetailRow label="Issue">
                    <Link
                      href={`/alerts?issue=${task.issue_id}`}
                      className="text-sm text-accent-brand hover:underline font-mono"
                    >
                      {task.issue_id.slice(0, 8)}...
                    </Link>
                  </DetailRow>
                )}
                {task.runbook_url && (
                  <DetailRow label="Runbook">
                    <a
                      href={task.runbook_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1 text-brand-pink"
                    >
                      Open <ExternalLink size={11} />
                    </a>
                  </DetailRow>
                )}
              </CardContent>
            </Card>

            {activeExec && (
              <Card className="border-l-2 border-l-brand-purple">
                <CardContent className="p-4">
                  <div className="flex items-center gap-2 text-sm">
                    <Brain size={14} className="text-brand-purple" />
                    <span className="text-text-primary">
                      Execution {activeExec.status}
                    </span>
                  </div>
                  <a
                    href={`/tasks/${taskId}/execution/${activeExec.id}`}
                    className="mt-2 inline-block text-[12px] text-brand-pink"
                  >
                    View live →
                  </a>
                </CardContent>
              </Card>
            )}
          </div>
        </div>
      </FadeIn>
    </div>
  );
}

const INVESTIGATION_STEPS = [
  { key: "started", label: "Investigation started", icon: Play },
  { key: "gathering_evidence", label: "Gathering evidence from cluster", icon: Search },
  { key: "analyzing", label: "The Brain is analyzing...", icon: Brain },
  { key: "completed", label: "Investigation complete", icon: CheckCircle },
] as const;

const STEP_ORDER: Record<string, number> = {
  started: 0,
  gathering_evidence: 1,
  analyzing: 2,
  completed: 3,
};

function InvestigationProgress({ state }: { state: InvestigationState }) {
  const currentStep = STEP_ORDER[state] ?? (state === "starting" ? 0 : 1);

  return (
    <Card className="border-purple-500/20">
      <CardContent className="p-4">
        <div className="mb-3 flex items-center gap-2">
          <Loader2 className="h-4 w-4 animate-spin text-purple-400" />
          <span className="text-sm font-medium">Investigation in progress</span>
        </div>
        <div className="space-y-2">
          {INVESTIGATION_STEPS.map((step, idx) => {
            const isCompleted = idx < currentStep;
            const isCurrent = idx === currentStep;
            const StepIcon = step.icon;

            return (
              <div key={step.key} className="flex items-center gap-2 text-sm">
                {isCompleted && (
                  <CheckCircle className="h-3.5 w-3.5 text-green-400" />
                )}
                {isCurrent && (
                  <Loader2 className="h-3.5 w-3.5 animate-spin text-purple-400" />
                )}
                {!isCompleted && !isCurrent && (
                  <StepIcon className="h-3.5 w-3.5 text-text-tertiary" />
                )}
                <span
                  className={
                    isCompleted
                      ? "text-text-secondary line-through"
                      : isCurrent
                        ? "font-medium text-text-primary"
                        : "text-text-tertiary"
                  }
                >
                  {step.label}
                </span>
              </div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}

function DetailRow({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-text-tertiary">{label}</span>
      {children}
    </div>
  );
}
