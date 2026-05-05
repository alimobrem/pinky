"use client";

import { useMemo, useState } from "react";
import { CheckCircle, XCircle, Shield, ShieldOff, Loader, Zap, Clock } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from "@/components/ui/alert-dialog";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { useSSE, type SSEConnectionState } from "@/hooks/use-sse";
import { api } from "@/lib/api";
import { shortTime } from "@/lib/format-date";
import { cn } from "@/lib/utils";

interface MonitorEvent {
  event_type: string;
  payload: Record<string, unknown>;
  occurred_at: string;
  sequence: number;
}

const MAX_EVENTS = 100;

interface ExecutionMonitorProps {
  executionId: string;
  onComplete?: () => void;
}

const EVENT_CONFIG: Record<string, { icon: React.ReactNode; color: string; label: string }> = {
  started: { icon: <Zap size={14} />, color: "text-accent-brain", label: "Execution started" },
  progress: { icon: <Loader size={14} />, color: "text-status-in-progress", label: "Step" },
  approval_required: { icon: <Shield size={14} />, color: "text-status-approval", label: "Approval required" },
  approval_granted: { icon: <CheckCircle size={14} />, color: "text-status-done", label: "Approved" },
  approval_rejected: { icon: <ShieldOff size={14} />, color: "text-status-blocked", label: "Rejected" },
  completed: { icon: <CheckCircle size={14} />, color: "text-status-done", label: "Completed" },
  failed: { icon: <XCircle size={14} />, color: "text-status-blocked", label: "Failed" },
  verified: { icon: <CheckCircle size={14} />, color: "text-status-done", label: "Verified" },
  timed_out: { icon: <Clock size={14} />, color: "text-status-blocked", label: "Timed out" },
};

function getConfig(eventType: string) {
  return EVENT_CONFIG[eventType] ?? { icon: <Zap size={14} />, color: "text-text-tertiary", label: eventType.replace(/_/g, " ") };
}

const CONNECTION_DOT: Record<SSEConnectionState, string> = {
  connecting: "bg-status-in-progress",
  connected: "bg-status-done",
  reconnecting: "bg-status-in-progress",
  disconnected: "bg-status-blocked",
};

const CONNECTION_LABELS: Record<SSEConnectionState, string> = {
  connecting: "Connecting...",
  connected: "Live",
  reconnecting: "Reconnecting...",
  disconnected: "Disconnected",
};

export function ExecutionMonitor({ executionId, onComplete }: ExecutionMonitorProps) {
  const [events, setEvents] = useState<MonitorEvent[]>([]);
  const [approveOpen, setApproveOpen] = useState(false);
  const [rejectOpen, setRejectOpen] = useState(false);
  const [rejectReason, setRejectReason] = useState("");

  const isTerminal = events.some(e =>
    e.event_type === "completed" || e.event_type === "failed" || e.event_type === "timed_out"
  );
  const needsApproval = events.some(e => e.event_type === "approval_required") &&
    !events.some(e => e.event_type === "approval_granted" || e.event_type === "approval_rejected");

  const sseHandlers = useMemo(() => ({
    update: (data: string) => {
      try {
        const envelope = JSON.parse(data);
        const payload = envelope.payload ?? {};
        const evt: MonitorEvent = {
          event_type: payload.event_type ?? envelope.type ?? "update",
          payload,
          occurred_at: envelope.occurred_at ?? new Date().toISOString(),
          sequence: envelope.sequence ?? 0,
        };
        setEvents(prev => [...prev, evt].slice(-MAX_EVENTS));
        if (evt.event_type === "completed" || evt.event_type === "failed" || evt.event_type === "verified") {
          onComplete?.();
        }
      } catch { /* ignore parse errors */ }
    },
  }), [onComplete]);

  const { state: sseState } = useSSE(`/api/v1/streams/executions/${executionId}`, {
    onEvent: sseHandlers,
    enabled: !isTerminal,
  });

  const handleApprove = async () => {
    try {
      await api.post(`/api/v1/executions/${executionId}/approve`, { changeset_digest: "approved" });
      toast.success("Execution approved");
    } catch (e) { toast.error(e instanceof Error ? e.message : "Failed to approve"); }
  };

  const handleReject = async () => {
    if (!rejectReason.trim()) return;
    try {
      await api.post(`/api/v1/executions/${executionId}/reject`, { reason: rejectReason });
      toast.success("Execution rejected");
      setRejectOpen(false);
      setRejectReason("");
    } catch (e) { toast.error(e instanceof Error ? e.message : "Failed to reject"); }
  };

  const lastProgress = [...events].reverse().find(e => e.event_type === "progress");
  const totalSteps = lastProgress?.payload?.total as number | undefined;
  const currentStep = lastProgress?.payload?.step as number | undefined;

  return (
    <div className="bg-bg-surface border border-border-default rounded-lg overflow-hidden">
      {/* Connection bar */}
      <div className="flex items-center gap-2 px-4 py-3 border-b border-border-subtle text-xs text-text-tertiary">
        <span className={cn("w-1.5 h-1.5 rounded-full shrink-0", CONNECTION_DOT[sseState])} />
        <span className="flex-1">{CONNECTION_LABELS[sseState]}</span>
        {totalSteps && currentStep && <span className="font-mono tabular">Step {currentStep}/{totalSteps}</span>}
      </div>

      {/* Progress bar */}
      {totalSteps && currentStep && (
        <div className="h-0.5 bg-bg-elevated">
          {/* eslint-disable-next-line react/forbid-component-props -- runtime-computed progress width */}
          <div className="h-full bg-accent-brain transition-all duration-300" style={{ width: `${(currentStep / totalSteps) * 100}%` }} />
        </div>
      )}

      {/* Events */}
      {events.length === 0 && !isTerminal && (
        <div className="py-6 text-center text-sm text-text-tertiary">Waiting for execution events...</div>
      )}

      <div className="flex flex-col">
        {events.map((evt, i) => {
          const config = getConfig(evt.event_type);
          return (
            <div key={i} className="flex items-start gap-3 px-4 py-3 border-b border-border-subtle last:border-b-0 animate-slide-in">
              <span className={cn("shrink-0 mt-0.5", config.color)}>{config.icon}</span>
              <div className="flex-1 flex flex-col gap-0.5">
                <span className="text-sm font-medium text-text-primary">{config.label}</span>
                {evt.event_type === "progress" && evt.payload?.description != null && (
                  <span className="text-xs text-text-secondary">{String(evt.payload.description)}</span>
                )}
                {evt.event_type === "failed" && evt.payload?.error != null && (
                  <span className="text-xs text-status-blocked font-mono">{String(evt.payload.error)}</span>
                )}
                {evt.event_type === "verified" && (
                  <span className="text-xs text-text-secondary">{evt.payload?.passed ? "Verification passed" : "Verification failed"}</span>
                )}
              </div>
              <span className="font-mono text-[11px] text-text-tertiary tabular shrink-0">{shortTime(evt.occurred_at)}</span>
            </div>
          );
        })}
      </div>

      {/* Approval controls */}
      {needsApproval && (
        <div className="flex items-center justify-between px-4 py-4 bg-[var(--status-approval-bg)] border-t border-status-approval/30">
          <span className="text-sm font-semibold text-status-approval">Approval required to continue</span>
          <div className="flex gap-2">
            <Button size="sm" className="bg-status-done hover:bg-status-done/90 h-7" onClick={() => setApproveOpen(true)}>
              <Shield size={14} /> Approve
            </Button>
            <Button size="sm" variant="destructive" className="h-7" onClick={() => setRejectOpen(true)}>
              <ShieldOff size={14} /> Reject
            </Button>
          </div>
        </div>
      )}

      <AlertDialog open={approveOpen} onOpenChange={setApproveOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Approve Execution</AlertDialogTitle>
            <AlertDialogDescription>This will allow The Brain to proceed with the remediation.</AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter><AlertDialogCancel>Cancel</AlertDialogCancel><AlertDialogAction onClick={handleApprove}>Approve</AlertDialogAction></AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      <Dialog open={rejectOpen} onOpenChange={v => { if (!v) { setRejectOpen(false); setRejectReason(""); } }}>
        <DialogContent>
          <DialogHeader><DialogTitle>Reject Execution</DialogTitle></DialogHeader>
          <div className="space-y-2"><Label>Reason *</Label><Textarea value={rejectReason} onChange={e => setRejectReason(e.target.value)} placeholder="Why are you rejecting?" rows={3} /></div>
          <DialogFooter>
            <Button variant="outline" onClick={() => { setRejectOpen(false); setRejectReason(""); }}>Cancel</Button>
            <Button variant="destructive" onClick={handleReject} disabled={!rejectReason.trim()}>Reject</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
