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
} from "lucide-react";

import { api } from "@/lib/api";
import { QUERY_KEYS } from "@/lib/constants";
import {
  taskOptions,
  investigationOptions,
  timelineOptions,
  executionsOptions,
} from "../queries";
import { StatusIndicator } from "@/components/shared/status-indicator";
import { PriorityBadge } from "@/components/shared/priority-badge";
import { ConfidenceBadge } from "@/components/shared/confidence-badge";
import { RelativeTime } from "@/components/shared/relative-time";
import { ApprovalGate } from "@/components/shared/approval-gate";
import { PageHeader } from "@/components/shared/page-header";
import { FadeIn } from "@/components/motion/fade-in";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { useState } from "react";
import { toast } from "sonner";

interface TaskDetailViewProps {
  taskId: string;
}

export function TaskDetailView({ taskId }: TaskDetailViewProps) {
  const router = useRouter();
  const qc = useQueryClient();
  const [blockReason, setBlockReason] = useState("");
  const [reassignId, setReassignId] = useState("");

  const { data: task } = useQuery(taskOptions(taskId));
  const { data: investigation } = useQuery(investigationOptions(taskId));
  const { data: timeline } = useQuery(timelineOptions(taskId));
  const { data: executions } = useQuery(executionsOptions(taskId));

  const invalidate = () => {
    qc.invalidateQueries({ queryKey: QUERY_KEYS.task(taskId) });
    qc.invalidateQueries({ queryKey: QUERY_KEYS.tasks() });
  };

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
      api.post("/api/v1/executions", {
        work_item_id: taskId,
        execution_type: "investigation",
      }),
    onSuccess: () => { invalidate(); toast.success("Investigation started"); },
  });

  if (!task) return null;

  const pendingExec = executions?.items?.find(
    (e) => e.status === "waiting_for_approval",
  );
  const activeExec = executions?.items?.find(
    (e) => e.status === "running" || e.status === "pending",
  );
  const events = timeline?.items ?? [];

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
                  <CardTitle className="text-[11px] font-semibold uppercase tracking-widest text-text-tertiary">
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

            {investigation?.has_investigation && (
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="flex items-center gap-2 text-[11px] font-semibold uppercase tracking-widest text-text-tertiary">
                    <Brain size={14} className="text-brand-purple" />
                    Investigation
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  {investigation.summary && (
                    <p className="text-sm leading-relaxed text-text-secondary">
                      {investigation.summary}
                    </p>
                  )}
                  {investigation.root_cause && (
                    <div>
                      <p className="text-[11px] font-semibold uppercase tracking-wider text-text-tertiary">
                        Root cause
                      </p>
                      <p className="mt-1 text-sm text-text-secondary">
                        {investigation.root_cause}
                      </p>
                    </div>
                  )}
                  {investigation.recommended_action && (
                    <div>
                      <p className="text-[11px] font-semibold uppercase tracking-wider text-text-tertiary">
                        Recommendation
                      </p>
                      <p className="mt-1 text-sm text-text-secondary">
                        {investigation.recommended_action}
                      </p>
                    </div>
                  )}
                  {investigation.confidence != null && (
                    <ConfidenceBadge value={investigation.confidence} />
                  )}
                </CardContent>
              </Card>
            )}

            {events.length > 0 && (
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-[11px] font-semibold uppercase tracking-widest text-text-tertiary">
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
                <CardTitle className="text-[11px] font-semibold uppercase tracking-widest text-text-tertiary">
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

                {!investigation?.has_investigation && !activeExec && (
                  <Button
                    size="sm"
                    variant="outline"
                    className="w-full justify-start gap-2"
                    onClick={() => investigate.mutate()}
                    disabled={investigate.isPending}
                  >
                    <Brain size={14} className="text-brand-purple" />
                    Start Investigation
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
                <CardTitle className="text-[11px] font-semibold uppercase tracking-widest text-text-tertiary">
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
