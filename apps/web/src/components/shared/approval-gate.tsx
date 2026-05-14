"use client";

import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { cn } from "@/lib/utils";
import { api } from "@/lib/api";
import { ShieldAlert, Check, X, Eye, Loader2, CheckCircle2, XCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";

interface PreviewStep {
  index: number;
  command: string;
  status: string;
  error?: string;
  action: string;
  resource: string;
  namespace: string;
}

interface ApprovalGateProps {
  executionId: string;
  resources?: Record<string, unknown>[];
  onApprove: (executionId: string) => void;
  onReject: (executionId: string) => void;
  isPending?: boolean;
  className?: string;
}

export function ApprovalGate({
  executionId,
  resources,
  onApprove,
  onReject,
  isPending,
  className,
}: ApprovalGateProps) {
  const [previewResults, setPreviewResults] = useState<PreviewStep[] | null>(null);

  const preview = useMutation({
    mutationFn: () =>
      api.post<{ steps: PreviewStep[] }>(`/api/v1/executions/${executionId}/preview`),
    onSuccess: (data) => setPreviewResults(data.steps),
  });

  const hasErrors = previewResults?.some((s) => s.status === "error");

  return (
    <div
      className={cn(
        "rounded-lg border border-status-approval/30 bg-status-approval/5 px-4 py-3",
        className,
      )}
    >
      <div className="flex items-center gap-3">
        <ShieldAlert size={18} className="shrink-0 text-status-approval" />
        <div className="min-w-0 flex-1">
          <p className="text-sm font-medium text-text-primary">
            Approval required
          </p>
          {resources && resources.length > 0 && (
            <p className="mt-0.5 text-caption text-text-secondary">
              {resources.length} resource{resources.length !== 1 ? "s" : ""} will be modified
            </p>
          )}
        </div>
        <div className="flex items-center gap-2">
          <Button
            size="sm"
            variant="outline"
            className="h-7 gap-1 text-text-secondary"
            onClick={() => preview.mutate()}
            disabled={preview.isPending}
          >
            {preview.isPending ? <Loader2 size={14} className="animate-spin" /> : <Eye size={14} />}
            Preview
          </Button>
          <AlertDialog>
            <AlertDialogTrigger asChild>
              <Button
                size="sm"
                variant="outline"
                className="h-7 gap-1 border-status-blocked/30 text-status-blocked hover:bg-status-blocked/10"
                disabled={isPending}
              >
                <X size={14} />
                Reject
              </Button>
            </AlertDialogTrigger>
            <AlertDialogContent>
              <AlertDialogHeader>
                <AlertDialogTitle>Reject execution?</AlertDialogTitle>
                <AlertDialogDescription>
                  This will stop the remediation workflow. The work item will remain in its current state.
                </AlertDialogDescription>
              </AlertDialogHeader>
              <AlertDialogFooter>
                <AlertDialogCancel>Cancel</AlertDialogCancel>
                <AlertDialogAction
                  className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                  onClick={() => onReject(executionId)}
                >
                  Reject
                </AlertDialogAction>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>
          <AlertDialog>
            <AlertDialogTrigger asChild>
              <Button
                size="sm"
                className="h-7 gap-1 bg-status-done text-text-inverse hover:bg-status-done/90"
                disabled={isPending || hasErrors === true}
              >
                <Check size={14} />
                Approve
              </Button>
            </AlertDialogTrigger>
            <AlertDialogContent>
              <AlertDialogHeader>
                <AlertDialogTitle>Approve execution?</AlertDialogTitle>
                <AlertDialogDescription>
                  The remediation will proceed with changes to {resources?.length ?? 0} resource{(resources?.length ?? 0) !== 1 ? "s" : ""}. This action cannot be undone.
                </AlertDialogDescription>
              </AlertDialogHeader>
              <AlertDialogFooter>
                <AlertDialogCancel>Cancel</AlertDialogCancel>
                <AlertDialogAction
                  className="bg-status-done text-text-inverse hover:bg-status-done/90"
                  onClick={() => onApprove(executionId)}
                >
                  Approve
                </AlertDialogAction>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>
        </div>
      </div>

      {previewResults && (
        <div className="mt-3 space-y-2 border-t border-border-subtle pt-3">
          <p className="text-caption font-medium text-text-secondary">
            Dry-run results
          </p>
          {previewResults.map((step) => (
            <div key={step.index} className="flex items-start gap-2 rounded bg-bg-surface px-2 py-1.5">
              {step.status === "ok" ? (
                <CheckCircle2 size={14} className="mt-0.5 shrink-0 text-status-done" />
              ) : (
                <XCircle size={14} className="mt-0.5 shrink-0 text-destructive" />
              )}
              <div className="min-w-0 flex-1">
                <code className="block font-mono text-xs text-brand-purple truncate">
                  $ {step.command}
                </code>
                {step.error && (
                  <p className="mt-0.5 text-caption text-destructive">{step.error}</p>
                )}
              </div>
            </div>
          ))}
          {hasErrors && (
            <p className="text-caption text-destructive">
              Some steps have errors — fix them before approving
            </p>
          )}
        </div>
      )}
    </div>
  );
}
