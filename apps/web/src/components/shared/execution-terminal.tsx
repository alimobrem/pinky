"use client";

import { useState } from "react";
import {
  ChevronRight,
  Copy,
  Check,
  CheckCircle2,
  XCircle,
  Loader2,
  Circle,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { ScrollArea } from "@/components/ui/scroll-area";
import { cn } from "@/lib/utils";
import { toast } from "sonner";

interface ExecutionEvent {
  id: string;
  execution_id: string;
  event_type: string;
  sequence: number;
  payload: Record<string, unknown>;
  occurred_at: string;
}

interface Step {
  index: number;
  total: number;
  description: string;
  commands: { command: string; output: string; exitCode: number }[];
  status: "pending" | "running" | "done" | "failed";
}

function deriveSteps(events: ExecutionEvent[]): {
  steps: Step[];
  status: "running" | "completed" | "failed";
  verificationPassed?: boolean;
} {
  const steps: Step[] = [];
  let current: Step | null = null;
  let status: "running" | "completed" | "failed" = "running";
  let verificationPassed: boolean | undefined;

  for (const event of events) {
    const p = event.payload;
    switch (event.event_type) {
      case "progress": {
        if (current) {
          current.status = "done";
        }
        current = {
          index: Number(p.step ?? steps.length + 1),
          total: Number(p.total ?? 0),
          description: String(p.description ?? ""),
          commands: [],
          status: "running",
        };
        steps.push(current);
        break;
      }
      case "command": {
        if (current) {
          const exitCode = Number(p.exit_code ?? 0);
          current.commands.push({
            command: String(p.command ?? ""),
            output: String(p.output ?? ""),
            exitCode,
          });
          if (exitCode !== 0) current.status = "failed";
        }
        break;
      }
      case "completed": {
        if (current) current.status = "done";
        status = "completed";
        verificationPassed = p.verification_passed as boolean | undefined;
        break;
      }
      case "failed": {
        if (current) current.status = "failed";
        status = "failed";
        break;
      }
      case "verified": {
        verificationPassed = p.passed as boolean | undefined;
        break;
      }
    }
  }

  return { steps, status, verificationPassed };
}

const statusConfig = {
  running: { label: "Running", className: "border-status-done/30 bg-status-done/10 text-status-done" },
  completed: { label: "Completed", className: "border-status-done/30 bg-status-done/10 text-status-done" },
  failed: { label: "Failed", className: "border-destructive/30 bg-destructive/10 text-destructive" },
} as const;

export interface ExecutionTerminalProps {
  events: ExecutionEvent[];
  className?: string;
  onCancel?: () => void;
}

export function ExecutionTerminal({ events, className, onCancel }: ExecutionTerminalProps) {
  const { steps, status, verificationPassed } = deriveSteps(events);
  const completedCount = steps.filter((s) => s.status === "done").length;
  const totalSteps = steps[0]?.total || steps.length;
  const cfg = statusConfig[status];

  return (
    <div className={cn("flex flex-col gap-0", className)}>
      {/* Header */}
      <div className="flex items-center justify-between border-b border-border-default px-4 py-3">
        <div className="flex items-center gap-3">
          <span className="text-sm font-medium text-text-primary">Execution Log</span>
          <Badge variant="outline" className={cn("text-caption", cfg.className)}>
            {status === "running" && <Loader2 size={10} className="animate-spin" />}
            {cfg.label}
          </Badge>
          {totalSteps > 0 && (
            <span className="text-caption text-text-tertiary tabular-nums">
              {completedCount}/{totalSteps} steps
            </span>
          )}
        </div>
        {status === "running" && onCancel && (
          <Button variant="ghost" size="sm" className="h-7 text-destructive text-caption" onClick={onCancel}>
            <XCircle size={12} className="mr-1" />
            Cancel
          </Button>
        )}
      </div>

      {/* Steps */}
      <ScrollArea className="flex-1">
        <div className="p-4 space-y-1">
          {steps.length === 0 && status === "running" && (
            <div className="flex items-center gap-2 py-6 justify-center text-sm text-text-tertiary">
              <Loader2 size={14} className="animate-spin" />
              Waiting for first step...
            </div>
          )}
          {steps.map((step) => (
            <StepRow key={step.index} step={step} />
          ))}
          {status === "completed" && verificationPassed !== undefined && (
            <div className={cn(
              "mt-2 flex items-center gap-2 rounded-md px-3 py-2 text-sm",
              verificationPassed
                ? "bg-status-done/10 text-status-done"
                : "bg-amber-500/10 text-amber-400",
            )}>
              {verificationPassed ? <CheckCircle2 size={14} /> : <XCircle size={14} />}
              Verification {verificationPassed ? "passed" : "failed"}
            </div>
          )}
        </div>
      </ScrollArea>
    </div>
  );
}

function StepRow({ step }: { step: Step }) {
  const isActive = step.status === "running" || step.status === "failed";
  const [open, setOpen] = useState(isActive);

  return (
    <Collapsible open={open} onOpenChange={setOpen}>
      <CollapsibleTrigger className="flex w-full items-center gap-2 rounded-md px-3 py-2 text-sm transition-colors hover:bg-bg-hover">
        <StepIcon status={step.status} />
        <span className="flex-1 text-left text-text-secondary">
          <span className="text-text-tertiary tabular-nums">Step {step.index}</span>
          {step.description && <span className="ml-1.5">{step.description}</span>}
        </span>
        <ChevronRight size={14} className={cn("text-text-tertiary transition-transform", open && "rotate-90")} />
      </CollapsibleTrigger>
      <CollapsibleContent>
        <div className="ml-7 space-y-2 pb-2">
          {step.commands.map((cmd, i) => (
            <CommandBlock key={i} command={cmd.command} output={cmd.output} exitCode={cmd.exitCode} />
          ))}
          {step.commands.length === 0 && step.status === "running" && (
            <div className="flex items-center gap-2 px-3 py-2 text-caption text-text-tertiary">
              <Loader2 size={12} className="animate-spin" /> Executing...
            </div>
          )}
        </div>
      </CollapsibleContent>
    </Collapsible>
  );
}

function StepIcon({ status }: { status: Step["status"] }) {
  switch (status) {
    case "done": return <CheckCircle2 size={14} className="shrink-0 text-status-done" />;
    case "failed": return <XCircle size={14} className="shrink-0 text-destructive" />;
    case "running": return <Loader2 size={14} className="shrink-0 animate-spin text-brand-purple" />;
    default: return <Circle size={14} className="shrink-0 text-text-tertiary" />;
  }
}

function CommandBlock({ command, output, exitCode }: { command: string; output: string; exitCode: number }) {
  const [copied, setCopied] = useState(false);

  const copy = () => {
    navigator.clipboard.writeText(command);
    setCopied(true);
    toast.success("Copied");
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="rounded-md border border-border-default bg-bg-base overflow-hidden">
      <div className="group flex items-start gap-2 px-3 py-2">
        <span className="text-status-done text-caption mt-0.5 select-none">$</span>
        <code className="flex-1 font-mono text-caption text-brand-purple break-all whitespace-pre-wrap">{command}</code>
        <Button variant="ghost" size="icon" className="h-5 w-5 shrink-0 opacity-0 group-hover:opacity-100 transition-opacity" onClick={copy}>
          {copied ? <Check size={10} /> : <Copy size={10} />}
        </Button>
      </div>
      {output && (
        <pre className={cn(
          "border-t border-border-default px-3 py-2 font-mono text-caption whitespace-pre-wrap break-all",
          exitCode === 0 ? "text-text-tertiary" : "text-destructive",
        )}>
          {output}
        </pre>
      )}
    </div>
  );
}
