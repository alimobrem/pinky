"use client";

import { cn } from "@/lib/utils";
import {
  Play,
  CheckCircle2,
  XCircle,
  ShieldAlert,
  Wrench,
  ArrowRight,
  Clock,
  RotateCcw,
  Timer,
  Loader,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import type { TimelineEvent } from "@pinky/contracts";
import { RelativeTime } from "@/components/shared/relative-time";
import { ApprovalGate } from "@/components/shared/approval-gate";
import { StalenessIndicator } from "@/components/shared/staleness-indicator";
import { Progress } from "@/components/ui/progress";
import type { SSEConnectionState } from "@/hooks/use-sse";

const EVENT_CONFIG: Record<string, { icon: LucideIcon; color: string; phase?: string }> = {
  started: { icon: Play, color: "text-status-in-progress", phase: "Detection" },
  progress: { icon: ArrowRight, color: "text-status-in-progress", phase: "Investigation" },
  tool_used: { icon: Wrench, color: "text-brand-purple", phase: "Investigation" },
  approval_required: { icon: ShieldAlert, color: "text-status-approval", phase: "Mitigation" },
  approval_granted: { icon: CheckCircle2, color: "text-status-done", phase: "Mitigation" },
  approval_rejected: { icon: XCircle, color: "text-status-blocked", phase: "Mitigation" },
  investigation_completed: { icon: CheckCircle2, color: "text-status-done", phase: "Investigation" },
  completed: { icon: CheckCircle2, color: "text-status-done", phase: "Resolution" },
  failed: { icon: XCircle, color: "text-status-blocked", phase: "Resolution" },
  verified: { icon: CheckCircle2, color: "text-status-done", phase: "Resolution" },
  timed_out: { icon: Timer, color: "text-status-approval", phase: "Resolution" },
  rolled_back: { icon: RotateCcw, color: "text-status-blocked", phase: "Resolution" },
};

interface ExecutionMonitorProps {
  events: TimelineEvent[];
  sseState: SSEConnectionState;
  lastUpdated: Date | null;
  pendingApproval?: boolean;
  executionId: string;
  onApprove?: (id: string) => void;
  onReject?: (id: string) => void;
  className?: string;
}

export function ExecutionMonitor({
  events,
  sseState,
  lastUpdated,
  pendingApproval,
  executionId,
  onApprove,
  onReject,
  className,
}: ExecutionMonitorProps) {
  let currentPhase = "";

  return (
    <div className={cn("space-y-0", className)}>
      <div className="flex items-center justify-between border-b border-border-subtle px-4 py-2">
        <span className="text-caption font-semibold uppercase tracking-wider text-text-tertiary">
          Execution Log
        </span>
        <StalenessIndicator state={sseState} lastUpdated={lastUpdated} />
      </div>

      <div className="divide-y divide-border-subtle">
        {events.map((event) => {
          const config = EVENT_CONFIG[event.event_type] ?? {
            icon: Clock,
            color: "text-text-tertiary",
          };
          const Icon = config.icon;
          const phase = config.phase;
          const showPhaseLabel = phase && phase !== currentPhase;
          if (phase) currentPhase = phase;

          const payload = event.payload as Record<string, string | number | undefined>;

          return (
            <div key={event.id}>
              {showPhaseLabel && (
                <div className="bg-bg-surface px-4 py-1.5 text-[10px] font-bold uppercase tracking-widest text-text-tertiary">
                  {phase}
                </div>
              )}
              <div className="flex items-start gap-3 px-4 py-3 transition-colors hover:bg-bg-hover">
                <div className={cn("mt-0.5 shrink-0", config.color)}>
                  <Icon size={14} />
                </div>
                <div className="min-w-0 flex-1 space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="text-sm text-text-primary">
                      {eventLabel(event.event_type, payload)}
                    </span>
                    <RelativeTime date={event.occurred_at} className="ml-auto" />
                  </div>
                  {payload.step_description && (
                    <p className="text-[12px] text-text-secondary">
                      {String(payload.step_description)}
                    </p>
                  )}
                  {payload.tool_name && (
                    <span className="inline-block rounded bg-bg-elevated px-1.5 py-0.5 font-mono text-caption text-brand-purple">
                      {String(payload.tool_name)}
                    </span>
                  )}
                  {typeof payload.progress === "number" && (
                    <Progress value={payload.progress * 100} className="h-1.5" />
                  )}
                </div>
              </div>

              {event.event_type === "approval_required" && pendingApproval && onApprove && onReject && (
                <div className="px-4 pb-3">
                  <ApprovalGate
                    executionId={executionId}
                    onApprove={onApprove}
                    onReject={onReject}
                  />
                </div>
              )}
            </div>
          );
        })}

        {events.length === 0 && (
          <div className="flex items-center gap-2 px-4 py-3 text-text-tertiary">
            <Loader size={14} className="animate-spin" />
            <span className="text-caption">Loading events...</span>
          </div>
        )}
        {events.length > 0 && !events.some((e) => ["completed", "failed", "timed_out", "rolled_back", "investigation_completed"].includes(e.event_type)) && (
          <div className="flex items-center gap-2 px-4 py-3 text-text-tertiary">
            <Loader size={14} className="animate-spin" />
            <span className="text-caption">In progress...</span>
          </div>
        )}
      </div>
    </div>
  );
}

function eventLabel(type: string, payload: Record<string, string | number | undefined>): string {
  switch (type) {
    case "started": return "Execution started";
    case "progress": return payload.step_description ? String(payload.step_description) : "Processing...";
    case "tool_used": return `Tool: ${payload.tool_name ?? "unknown"}`;
    case "approval_required": return "Approval required to proceed";
    case "approval_granted": return "Approved";
    case "approval_rejected": return payload.reason ? `Rejected: ${payload.reason}` : "Rejected";
    case "investigation_completed": return payload.summary ? String(payload.summary) : "Investigation complete";
    case "completed": return "Execution completed successfully";
    case "failed": return payload.error ? `Failed: ${payload.error}` : "Execution failed";
    case "verified": return "Changes verified";
    case "timed_out": return "Execution timed out";
    case "rolled_back": return "Changes rolled back";
    default: return type.replace(/_/g, " ");
  }
}
