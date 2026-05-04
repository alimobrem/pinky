"use client";

import { useEffect, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, Brain, CheckCircle, Play, ChevronDown, ChevronRight, Zap, Shield, ShieldOff, UserPlus, Ban, Rocket, Link2 } from "lucide-react";
import { toast } from "sonner";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import type { WorkItem, Execution, Investigation, TimelineEvent, PaginatedResponse } from "@pinky/contracts";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from "@/components/ui/alert-dialog";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { ExecutionMonitor } from "@/components/execution-monitor";
import { api } from "@/lib/api";
import { relativeTime, shortTime } from "@/lib/format-date";
import { cn } from "@/lib/utils";
import { STATUS_BG, PRIORITY_BG, confColor, confLabel } from "@/lib/status-colors";

const EVENT_ICONS: Record<string, string> = { started: "\u{1F680}", completed: "✅", failed: "❌", investigation_completed: "\u{1F50D}", verified: "✓" };

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

  const { data: pendingExecData } = useQuery({
    queryKey: ["pending-execution", taskId],
    queryFn: () => api.get<PaginatedResponse<Execution>>(`/api/v1/executions?work_item_id=${taskId}&status=pending`),
    enabled: item?.status === "waiting_for_approval",
  });

  const events = eventsData?.items ?? [];
  const inv = investigation?.has_investigation ? investigation : null;
  const pendingExecution = (pendingExecData?.items ?? [])[0] ?? null;

  const actionMutation = useMutation({
    mutationFn: (action: string) => api.post<WorkItem>(`/api/v1/work-items/${taskId}/${action}`),
    onSuccess: (_, action) => { toast.success(`Task ${action}ed`); invalidateAll(); },
    onError: (e: Error) => toast.error(e.message),
  });

  const blockMutation = useMutation({
    mutationFn: () => api.post<WorkItem>(`/api/v1/work-items/${taskId}/block`, { reason: blockReason }),
    onSuccess: () => { toast.success("Task blocked"); setBlockOpen(false); setBlockReason(""); invalidateAll(); },
    onError: (e: Error) => toast.error(e.message),
  });

  const reassignMutation = useMutation({
    mutationFn: () => api.post<WorkItem>(`/api/v1/work-items/${taskId}/reassign?assignee_id=${reassignId}`),
    onSuccess: () => { toast.success("Task reassigned"); setReassignOpen(false); setReassignId(""); invalidateAll(); },
    onError: (e: Error) => toast.error(e.message),
  });

  const approveMutation = useMutation({
    mutationFn: () => api.post(`/api/v1/executions/${pendingExecution!.id}/approve`, { changeset_digest: "approved" }),
    onSuccess: () => { toast.success("Approved"); setApproveOpen(false); invalidateAll(); },
    onError: (e: Error) => toast.error(e.message),
  });

  const rejectMutation = useMutation({
    mutationFn: () => api.post(`/api/v1/executions/${pendingExecution!.id}/reject`, { reason: rejectReason }),
    onSuccess: () => { toast.success("Rejected"); setRejectOpen(false); setRejectReason(""); invalidateAll(); },
    onError: (e: Error) => toast.error(e.message),
  });

  const ticketMutation = useMutation({
    mutationFn: () => api.post(`/api/v1/work-items/${taskId}/annotations`, { annotations: { ticket_url: ticketUrl } }),
    onSuccess: () => { toast.success("Ticket linked"); setTicketOpen(false); setTicketUrl(""); invalidateAll(); },
    onError: (e: Error) => toast.error(e.message),
  });

  const triggerInvestigation = async () => {
    setInvestigating(true);
    try {
      const existing = await api.get<PaginatedResponse<Execution>>(`/api/v1/executions?work_item_id=${taskId}&status=pending`);
      if ((existing.items || []).length > 0) { toast.warning("Investigation already in progress"); setInvestigating(false); return; }
      await api.post(`/api/v1/executions?work_item_id=${taskId}&execution_type=investigation`);
      toast.info("Brain investigation started...");
      let attempts = 0;
      if (pollRef.current) clearInterval(pollRef.current);
      pollRef.current = setInterval(async () => {
        attempts++;
        try {
          const inv = await api.get<Investigation>(`/api/v1/work-items/${taskId}/investigation`);
          if (inv.has_investigation || attempts >= 10) {
            if (pollRef.current) clearInterval(pollRef.current);
            pollRef.current = null;
            setInvestigating(false);
            invalidateAll();
            if (inv.has_investigation) toast.success("Investigation complete");
          }
        } catch { if (pollRef.current) clearInterval(pollRef.current); pollRef.current = null; setInvestigating(false); }
      }, 3000);
    } catch { toast.error("Network error"); setInvestigating(false); }
  };

  const startRemediation = async () => {
    try {
      const result = await api.post<{ id: string }>(`/api/v1/executions?work_item_id=${taskId}&execution_type=remediation`);
      setActiveRemediationId(result.id);
      toast.info("Remediation started");
    } catch (e) { toast.error(e instanceof Error ? e.message : "Failed"); }
  };

  useEffect(() => { return () => { if (pollRef.current) clearInterval(pollRef.current); }; }, []);

  const acting = actionMutation.isPending || blockMutation.isPending || reassignMutation.isPending || investigating;

  // Keyboard shortcuts
  useEffect(() => {
    if (!item || item.status === "done") return;
    const anyDialogOpen = blockOpen || reassignOpen || rejectOpen || approveOpen || reinvestigateOpen;
    const handler = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement || e.target instanceof HTMLSelectElement) return;
      if (acting || anyDialogOpen) return;
      switch (e.key) {
        case "a": if (item.status === "ready") actionMutation.mutate("accept"); break;
        case "s": if (item.status === "accepted" || item.status === "blocked") actionMutation.mutate("start"); break;
        case "b": if (item.status === "in_progress") setBlockOpen(true); break;
        case "c": if (item.status === "in_progress") actionMutation.mutate("complete"); break;
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [item, acting, blockOpen, reassignOpen, rejectOpen, approveOpen, reinvestigateOpen]);

  if (isLoading) return (
    <div className="flex flex-col gap-4">
      {[1, 2, 3].map(i => <div key={i} className={`skeleton rounded-lg ${i === 1 ? "h-[60px]" : "h-[180px]"}`} />)}
    </div>
  );

  if (!item) return <div className="text-center text-text-tertiary py-16">Task not found.</div>;

  const isDone = item.status === "done";

  return (
    <div>
      {/* Back + Actions */}
      <div className="flex items-center justify-between mb-4">
        <button onClick={() => router.push("/tasks")} className="flex items-center gap-2 text-sm text-text-secondary hover:text-text-primary bg-transparent border-none cursor-pointer">
          <ArrowLeft size={16} /> Back to Tasks
        </button>
        <div className="flex gap-1.5 flex-wrap justify-end">
          {item.status === "ready" && <Button size="sm" onClick={() => actionMutation.mutate("accept")} disabled={acting}>Accept</Button>}
          {(item.status === "accepted" || item.status === "blocked") && <Button size="sm" onClick={() => actionMutation.mutate("start")} disabled={acting}><Play size={13} /> Start</Button>}
          {item.status === "in_progress" && (
            <>
              <Button size="sm" variant="destructive" onClick={() => setBlockOpen(true)} disabled={acting}><Ban size={13} /> Block</Button>
              <Button size="sm" variant="secondary" onClick={() => actionMutation.mutate("complete")} disabled={acting}><CheckCircle size={13} /> Complete</Button>
            </>
          )}
          {item.status === "waiting_for_approval" && pendingExecution && (
            <>
              <Button size="sm" onClick={() => setApproveOpen(true)} disabled={acting}><Shield size={13} /> Approve</Button>
              <Button size="sm" variant="destructive" onClick={() => setRejectOpen(true)} disabled={acting}><ShieldOff size={13} /> Reject</Button>
            </>
          )}
          {!isDone && <Button size="sm" variant="outline" onClick={() => setReassignOpen(true)} disabled={acting}><UserPlus size={13} /></Button>}
          {!isDone && <Button size="sm" variant="outline" onClick={() => setTicketOpen(true)}><Link2 size={13} /></Button>}
        </div>
      </div>

      {/* Title + badges */}
      <div className="mb-6">
        <h1 className="text-lg font-semibold tracking-tight mb-3 leading-snug">{item.title}</h1>
        <div className="flex gap-3 items-center flex-wrap">
          <span className={cn("text-[11px] px-2 py-0.5 rounded-sm font-semibold text-white uppercase", PRIORITY_BG[item.priority])}>{item.priority}</span>
          <span className={cn("text-[11px] px-2 py-0.5 rounded-sm font-semibold text-white uppercase", STATUS_BG[item.status])}>{item.status.replace(/_/g, " ")}</span>
          {Object.entries(item.labels).map(([k, v]) => <span key={k} className="text-[11px] px-1.5 py-0.5 bg-bg-elevated rounded-sm text-text-secondary">{k}={v}</span>)}
          {item.annotations?.ticket_url && (
            <a href={item.annotations.ticket_url} target="_blank" rel="noopener noreferrer" className="flex items-center gap-1 text-xs text-accent-brand">
              <Link2 size={12} /> {item.annotations.ticket_url.replace(/^https?:\/\//, "").slice(0, 40)}
            </a>
          )}
        </div>
      </div>

      {item.status === "blocked" && item.blocked_reason && (
        <div className="flex items-center gap-2 p-3 px-4 mb-5 rounded-md bg-status-blocked/10 border border-status-blocked/30 text-status-blocked text-sm font-medium">
          <Ban size={14} /><span>Blocked: {item.blocked_reason}</span>
        </div>
      )}

      <div className="grid grid-cols-1 xl:grid-cols-[1fr_340px] gap-5 mb-6">
        <div className="flex flex-col gap-4">
          <section className="bg-bg-surface border border-border-default rounded-lg p-5">
            <h2 className="text-xs font-semibold uppercase tracking-wider text-text-tertiary mb-3 pb-2 border-b border-border-subtle">Summary</h2>
            {item.why_now && <div className="mb-4"><div className="text-xs font-semibold text-text-tertiary mb-1">Why now</div><div className="text-sm leading-relaxed">{item.why_now}</div></div>}
            <div className="text-xs font-semibold text-text-tertiary">Created {relativeTime(item.created_at)}</div>
          </section>

          {inv ? (
            <section className="bg-bg-surface border border-border-default rounded-lg p-5">
              <h2 className="text-xs font-semibold uppercase tracking-wider text-text-tertiary mb-3 pb-2 border-b border-border-subtle flex items-center gap-2">
                <Brain size={14} className="text-accent-brain" /> Investigation Results
              </h2>
              {inv.summary && <div className="whitespace-pre-wrap text-sm leading-relaxed">{inv.summary}</div>}
              {inv.root_cause && inv.root_cause !== inv.summary && (
                <div>
                  <button onClick={() => setShowReasoning(!showReasoning)} className="flex items-center gap-2 text-sm font-semibold text-accent-brain bg-transparent border-none cursor-pointer mt-2">
                    {showReasoning ? <ChevronDown size={14} /> : <ChevronRight size={14} />} View full analysis
                  </button>
                  {showReasoning && <div className="mt-3 pt-3 border-t border-border-brain text-sm text-text-secondary leading-relaxed whitespace-pre-wrap">{inv.root_cause}</div>}
                </div>
              )}
              <div className="text-xs font-semibold text-text-tertiary mt-3">Investigated {inv.created_at ? relativeTime(inv.created_at) : "recently"}</div>
            </section>
          ) : (
            <section className="bg-bg-surface border border-border-default rounded-lg p-5 text-center">
              <Brain size={24} className="text-text-tertiary mb-3 mx-auto" />
              <p className="text-text-secondary mb-2">No investigation data yet.</p>
              <p className="text-sm text-text-tertiary">Trigger an investigation to have The Brain analyze this issue.</p>
            </section>
          )}
        </div>

        <div className="flex flex-col gap-4">
          <div className="bg-[var(--accent-brain-bg)] border border-border-brain border-l-3 border-l-accent-brain rounded-lg p-5 shadow-brain-glow">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2 text-sm font-semibold text-accent-brain"><Brain size={16} /> The Brain recommends</div>
              {(inv?.confidence ?? item.confidence) != null && (
                <div className="text-right">
                  <div className={cn("tabular text-lg font-bold", confColor((inv?.confidence ?? item.confidence)!))}>{Math.round((inv?.confidence ?? item.confidence)! * 100)}%</div>
                  <div className="text-[11px] text-text-tertiary">{confLabel((inv?.confidence ?? item.confidence)!)}</div>
                </div>
              )}
            </div>
            <div className="text-sm text-text-primary leading-relaxed">{inv?.recommended_action || item.recommended_next_step || "No recommendation available yet."}</div>
            {item.runbook_url && (
              <div className="mt-3 pt-3 border-t border-border-brain">
                <a href={item.runbook_url} target="_blank" rel="noopener noreferrer" className="text-accent-brain text-sm">View runbook</a>
              </div>
            )}
          </div>

          {inv ? (
            <Button variant="outline" className="w-full border-border-brain text-accent-brain hover:bg-accent-brain/10" onClick={() => setReinvestigateOpen(true)} disabled={acting}>
              <Zap size={16} /> {investigating ? "Brain is investigating..." : "Re-investigate"}
            </Button>
          ) : (
            <Button variant="outline" className="w-full border-border-brain text-accent-brain hover:bg-accent-brain/10" onClick={triggerInvestigation} disabled={acting}>
              <Zap size={16} /> {investigating ? "Brain is investigating..." : "Run Brain Investigation"}
            </Button>
          )}

          {inv?.recommended_action && !activeRemediationId && !isDone && (
            <Button variant="outline" className="w-full border-accent-brand-dim text-accent-brand hover:bg-accent-brand/10" onClick={startRemediation} disabled={acting}>
              <Rocket size={16} /> Start Remediation
            </Button>
          )}

          {activeRemediationId && (
            <div>
              <div className="text-xs font-semibold text-text-tertiary uppercase tracking-wider mb-2">Live Execution</div>
              <ExecutionMonitor executionId={activeRemediationId} onComplete={invalidateAll} />
              <Link href={`/tasks/${taskId}/execution/${activeRemediationId}`} className="text-xs text-accent-brand block mt-2">View full execution detail</Link>
            </div>
          )}
        </div>
      </div>

      <section className="bg-bg-surface border border-border-default rounded-lg p-5">
        <h2 className="text-xs font-semibold uppercase tracking-wider text-text-tertiary mb-3 pb-2 border-b border-border-subtle">Execution Timeline</h2>
        {events.length === 0 ? (
          <p className="text-sm text-text-tertiary py-4">No execution events yet.</p>
        ) : (
          <div>
            {events.map(e => (
              <div key={e.id} className="grid grid-cols-[32px_80px_1fr] gap-2 py-3 items-start [&+&]:border-t [&+&]:border-border-subtle">
                <div className="flex justify-center">
                  <div className={cn("w-2.5 h-2.5 rounded-full mt-1",
                    e.event_type.includes("failed") ? "bg-status-blocked" :
                    e.event_type.includes("completed") || e.event_type.includes("verified") ? "bg-status-done" : "bg-accent-brain"
                  )} />
                </div>
                <span className="font-mono text-[11px] text-text-tertiary tabular">{shortTime(e.occurred_at)}</span>
                <div>
                  <Link href={`/tasks/${taskId}/execution/${e.execution_id}`} className="text-sm font-medium text-text-primary no-underline hover:text-accent-brand">
                    {EVENT_ICONS[e.event_type] || "•"} {e.event_type.replace(/_/g, " ")}
                  </Link>
                  {e.payload && Object.keys(e.payload).length > 0 && (
                    <div className="text-xs text-text-tertiary mt-0.5">
                      {Object.entries(e.payload).slice(0, 3).map(([k, v]) => <span key={k} className="mr-3">{k}: {String(v)}</span>)}
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      <Dialog open={blockOpen} onOpenChange={v => { if (!v) { setBlockOpen(false); setBlockReason(""); } }}>
        <DialogContent><DialogHeader><DialogTitle>Mark as Blocked</DialogTitle></DialogHeader>
          <div className="space-y-2"><Label>Reason *</Label><Textarea value={blockReason} onChange={e => setBlockReason(e.target.value)} placeholder="Why is this task blocked?" rows={3} /></div>
          <DialogFooter><Button variant="outline" onClick={() => { setBlockOpen(false); setBlockReason(""); }}>Cancel</Button><Button variant="destructive" onClick={() => blockMutation.mutate()} disabled={!blockReason.trim()}>Block Task</Button></DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={reassignOpen} onOpenChange={v => { if (!v) { setReassignOpen(false); setReassignId(""); } }}>
        <DialogContent><DialogHeader><DialogTitle>Reassign Task</DialogTitle></DialogHeader>
          <div className="space-y-2"><Label>Assignee ID *</Label><Input value={reassignId} onChange={e => setReassignId(e.target.value)} placeholder="UUID of the new assignee" /></div>
          <DialogFooter><Button variant="outline" onClick={() => { setReassignOpen(false); setReassignId(""); }}>Cancel</Button><Button onClick={() => reassignMutation.mutate()} disabled={!reassignId.trim()}>Reassign</Button></DialogFooter>
        </DialogContent>
      </Dialog>

      <AlertDialog open={approveOpen} onOpenChange={setApproveOpen}>
        <AlertDialogContent><AlertDialogHeader><AlertDialogTitle>Approve Execution</AlertDialogTitle><AlertDialogDescription>This will allow The Brain to proceed with the recommended remediation.</AlertDialogDescription></AlertDialogHeader>
          <AlertDialogFooter><AlertDialogCancel>Cancel</AlertDialogCancel><AlertDialogAction onClick={() => approveMutation.mutate()}>Approve</AlertDialogAction></AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      <Dialog open={rejectOpen} onOpenChange={v => { if (!v) { setRejectOpen(false); setRejectReason(""); } }}>
        <DialogContent><DialogHeader><DialogTitle>Reject Execution</DialogTitle></DialogHeader>
          <div className="space-y-2"><Label>Reason *</Label><Textarea value={rejectReason} onChange={e => setRejectReason(e.target.value)} placeholder="Why are you rejecting?" rows={3} /></div>
          <DialogFooter><Button variant="outline" onClick={() => { setRejectOpen(false); setRejectReason(""); }}>Cancel</Button><Button variant="destructive" onClick={() => rejectMutation.mutate()} disabled={!rejectReason.trim()}>Reject</Button></DialogFooter>
        </DialogContent>
      </Dialog>

      <AlertDialog open={reinvestigateOpen} onOpenChange={setReinvestigateOpen}>
        <AlertDialogContent><AlertDialogHeader><AlertDialogTitle>Re-investigate</AlertDialogTitle><AlertDialogDescription>This will start a new investigation, overwriting cached results.</AlertDialogDescription></AlertDialogHeader>
          <AlertDialogFooter><AlertDialogCancel>Cancel</AlertDialogCancel><AlertDialogAction onClick={() => { setReinvestigateOpen(false); triggerInvestigation(); }}>Re-investigate</AlertDialogAction></AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
      {/* Ticket Link Dialog */}
      <Dialog open={ticketOpen} onOpenChange={v => { if (!v) { setTicketOpen(false); setTicketUrl(""); } }}>
        <DialogContent><DialogHeader><DialogTitle>Link External Ticket</DialogTitle></DialogHeader>
          <div className="space-y-2"><Label>Ticket URL *</Label><Input value={ticketUrl} onChange={e => setTicketUrl(e.target.value)} placeholder="https://jira.example.com/browse/OPS-123" /></div>
          <DialogFooter><Button variant="outline" onClick={() => { setTicketOpen(false); setTicketUrl(""); }}>Cancel</Button><Button onClick={() => ticketMutation.mutate()} disabled={!ticketUrl.trim()}>Link</Button></DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
