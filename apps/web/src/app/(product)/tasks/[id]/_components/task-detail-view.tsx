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
import { MarkdownContent } from "@/components/shared/markdown-content";
import { RemediationPlan } from "./remediation-plan";
import { BrainChat } from "./brain-chat";
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
import { Textarea } from "@/components/ui/textarea";
import { useState, useEffect, useMemo } from "react";
import { toast } from "sonner";
import type { Execution } from "@pinky/contracts";
import { ResourceEditor } from "@/components/shared/resource-editor";

interface TaskDetailViewProps {
  taskId: string;
}

export function TaskDetailView({ taskId }: TaskDetailViewProps) {
  const router = useRouter();
  const qc = useQueryClient();
  const [blockReason, setBlockReason] = useState("");

  const { data: task } = useQuery(taskOptions(taskId));
  const { data: executions } = useQuery(executionsOptions(taskId));
  const { data: investigation } = useQuery(investigationOptions(taskId));
  const { data: timeline } = useQuery(timelineOptions(taskId));

  const invalidateAll = () => {
    qc.invalidateQueries({ queryKey: QUERY_KEYS.task(taskId) });
    qc.invalidateQueries({ queryKey: QUERY_KEYS.tasks() });
    qc.invalidateQueries({ queryKey: QUERY_KEYS.taskInvestigation(taskId) });
    qc.invalidateQueries({ queryKey: QUERY_KEYS.taskTimeline(taskId) });
    qc.invalidateQueries({ queryKey: [...QUERY_KEYS.executions(), taskId] });
  };

  // SSE: real-time updates for this work item
  useSSE("/api/v1/streams/events", {
    onEvent: { update: () => invalidateAll() },
  });

  const accept = useMutation({
    mutationFn: () => api.post(`/api/v1/work-items/${taskId}/accept`),
    onSuccess: () => { invalidateAll(); toast.success("Task accepted"); },
  });
  const start = useMutation({
    mutationFn: () => api.post(`/api/v1/work-items/${taskId}/start`),
    onSuccess: () => { invalidateAll(); toast.success("Task started"); },
  });
  const complete = useMutation({
    mutationFn: () => api.post(`/api/v1/work-items/${taskId}/complete`),
    onSuccess: () => { invalidateAll(); toast.success("Task completed"); },
  });
  const block = useMutation({
    mutationFn: (reason: string) =>
      api.post(`/api/v1/work-items/${taskId}/block`, { reason }),
    onSuccess: () => { invalidateAll(); setBlockReason(""); toast.success("Task blocked"); },
  });
  const take = useMutation({
    mutationFn: () => api.post(`/api/v1/work-items/${taskId}/take`),
    onSuccess: () => { invalidateAll(); toast.success("Task assigned to you"); },
    onError: () => toast.error("Failed to take task"),
  });
  const approve = useMutation({
    mutationFn: (execId: string) => api.post(`/api/v1/executions/${execId}/approve`),
    onSuccess: () => { invalidateAll(); toast.success("Execution approved"); },
  });
  const reject = useMutation({
    mutationFn: (execId: string) => api.post(`/api/v1/executions/${execId}/reject`),
    onSuccess: () => { invalidateAll(); toast.success("Execution rejected"); },
  });
  const investigate = useMutation({
    mutationFn: () =>
      api.post<Execution>(
        `/api/v1/executions?work_item_id=${encodeURIComponent(taskId)}&execution_type=investigation`,
      ),
    onSuccess: () => {
      invalidateAll();
      toast.success("Investigation started");
    },
    onError: () => toast.error("Failed to start investigation"),
  });

  const resourceInfo = useMemo(() => {
    if (!task) return null;
    const labels = task.labels ?? {};
    let kind = labels.component ?? "pod";
    let ns = labels.namespace ?? "";
    let name = labels.name ?? "";
    if (!name && task.title) {
      const m = task.title.match(/^(\w+)\s+(\S+)\/(\S+)\s+/);
      if (m) {
        kind = m[1];
        ns = ns || m[2];
        name = m[3];
      }
    }
    return kind && ns && name ? { kind, namespace: ns, name, clusterId: task.cluster_id } : null;
  }, [task]);

  if (!task) return null;

  // Derived state — no useState, no useEffect, no state machine
  const activeExec = executions?.items?.find(
    (e) => (e.status === "running" || e.status === "pending") && e.execution_type === "investigation",
  );
  const pendingExec = executions?.items?.find(
    (e) => e.status === "waiting_for_approval",
  );
  const events = timeline?.items ?? [];
  const hasResults = investigation?.has_investigation === true;
  const isInvestigating = !hasResults && (!!activeExec || investigate.isPending);

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

            {isInvestigating && (
              <InvestigationProgress execution={activeExec} />
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
                    <MarkdownContent content={investigation.recommended_action} />

                    <Collapsible>
                      <CollapsibleTrigger className="flex items-center gap-1 mt-3 text-xs text-text-secondary hover:text-text-primary">
                        <ChevronRight className="h-3 w-3" />
                        View reasoning
                      </CollapsibleTrigger>
                      <CollapsibleContent className="mt-3 space-y-4">
                        {investigation.summary && (
                          <div>
                            <span className="text-caption font-semibold uppercase tracking-widest text-text-tertiary">
                              Summary
                            </span>
                            <MarkdownContent content={investigation.summary} className="mt-1" />
                          </div>
                        )}
                        {investigation.root_cause && (
                          <div>
                            <span className="text-caption font-semibold uppercase tracking-widest text-text-tertiary">
                              Root Cause
                            </span>
                            <MarkdownContent content={investigation.root_cause} className="mt-1" />
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

            {investigation?.has_investigation && (
              <RemediationPlan
                steps={investigation.remediation_steps ?? []}
                manualCommands={investigation.manual_commands ?? []}
                clusterName={task?.cluster_id}
              />
            )}

            {resourceInfo && (
              <ResourceEditor
                clusterId={resourceInfo.clusterId}
                namespace={resourceInfo.namespace}
                kind={resourceInfo.kind}
                name={resourceInfo.name}
              />
            )}

            <BrainChat taskId={taskId} />

            {events.length > 0 && (
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-caption font-semibold uppercase tracking-widest text-text-tertiary">
                    Timeline
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    {events.map((event) => {
                      const payload = (event.payload ?? {}) as Record<string, string | number | undefined>;
                      const label = timelineLabel(event.event_type, payload);
                      return (
                        <div
                          key={event.id}
                          className="flex items-start gap-3 rounded-md px-2 py-1.5 text-sm hover:bg-bg-hover"
                        >
                          <span className="mt-1.5 w-2 h-2 rounded-full bg-brand-purple shrink-0" />
                          <div className="flex-1 min-w-0">
                            <span className="text-text-secondary">{label}</span>
                            {payload.tool_name && (
                              <span className="ml-2 inline-block rounded bg-bg-elevated px-1.5 py-0.5 font-mono text-caption text-brand-purple">
                                {String(payload.tool_name)}
                              </span>
                            )}
                          </div>
                          <RelativeTime date={event.occurred_at} className="shrink-0" />
                        </div>
                      );
                    })}
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

                {!isInvestigating && (
                  <Button
                    size="sm"
                    variant="outline"
                    className="w-full justify-start gap-2"
                    onClick={() => investigate.mutate()}
                    disabled={investigate.isPending}
                  >
                    <Brain size={14} className="text-brand-purple" />
                    {investigate.isPending ? "Starting..." : hasResults ? "Re-investigate" : "Start Investigation"}
                  </Button>
                )}
                {isInvestigating && activeExec && (
                  <Button
                    size="sm"
                    variant="outline"
                    className="w-full justify-start gap-2 border-amber-500/30 text-amber-400"
                    onClick={async () => {
                      try {
                        await api.post(`/api/v1/executions/${activeExec.id}/cancel`);
                        invalidateAll();
                        toast.info("Investigation cancelled");
                      } catch {
                        toast.error("Failed to cancel");
                      }
                    }}
                  >
                    <XCircle size={14} />
                    Cancel Investigation
                  </Button>
                )}

                <Button
                  size="sm"
                  variant="ghost"
                  className="w-full justify-start gap-2 text-text-secondary"
                  onClick={() => take.mutate()}
                  disabled={take.isPending}
                >
                  <UserPlus size={14} />
                  {take.isPending ? "Assigning..." : "Take this task"}
                </Button>
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

function InvestigationProgress({ execution }: { execution?: { created_at: string; started_at?: string | null; status: string } }) {
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    if (!execution) return;
    const start = new Date(execution.started_at ?? execution.created_at).getTime();
    const tick = () => setElapsed(Math.floor((Date.now() - start) / 1000));
    tick();
    const timer = setInterval(tick, 1000);
    return () => clearInterval(timer);
  }, [execution]);

  const phase =
    elapsed < 5 ? 0 :
    elapsed < 25 ? 1 :
    2;

  const steps = [
    { label: "Gathering evidence from cluster", threshold: 0 },
    { label: "The Brain is analyzing...", threshold: 5 },
    { label: "Finalizing investigation", threshold: 25 },
  ];

  return (
    <Card className="border-brand-purple/20 bg-brand-purple/5">
      <CardContent className="p-4">
        <div className="mb-3 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Loader2 className="h-4 w-4 animate-spin text-brand-purple" />
            <span className="text-sm font-medium text-text-primary">Investigation in progress</span>
          </div>
          <span className="font-mono text-caption tabular-nums text-text-tertiary">{elapsed}s</span>
        </div>
        <div className="space-y-2">
          {steps.map((step, idx) => (
            <div key={idx} className="flex items-center gap-2 text-sm">
              {idx < phase ? (
                <CheckCircle className="h-3.5 w-3.5 text-status-done" />
              ) : idx === phase ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin text-brand-purple" />
              ) : (
                <div className="h-3.5 w-3.5 rounded-full border border-border-default" />
              )}
              <span className={
                idx < phase ? "text-text-secondary" :
                idx === phase ? "font-medium text-text-primary" :
                "text-text-tertiary"
              }>
                {step.label}
              </span>
            </div>
          ))}
        </div>
        <div className="mt-3 h-1.5 rounded-full bg-bg-hover overflow-hidden">
          <div
            className="h-full rounded-full bg-brand-purple transition-all duration-1000"
            style={{ width: `${Math.min(95, (elapsed / 35) * 100)}%` }}
          />
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

function timelineLabel(type: string, payload: Record<string, string | number | undefined>): string {
  switch (type) {
    case "started": return "Execution started";
    case "progress": return payload.step_description ? String(payload.step_description) : "Processing...";
    case "tool_used": return `Tool: ${payload.tool_name ?? "unknown"}`;
    case "investigation_completed": return payload.summary ? String(payload.summary) : "Investigation complete";
    case "completed": return "Execution completed successfully";
    case "failed": return payload.error ? `Failed: ${payload.error}` : "Execution failed";
    default: return type.replace(/_/g, " ");
  }
}
