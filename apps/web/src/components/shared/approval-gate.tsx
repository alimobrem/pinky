"use client";

import { cn } from "@/lib/utils";
import { ShieldAlert, Check, X } from "lucide-react";
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
  return (
    <div
      className={cn(
        "flex items-center gap-3 rounded-lg border border-status-approval/30 bg-status-approval/5 px-4 py-3",
        className,
      )}
    >
      <ShieldAlert size={18} className="shrink-0 text-status-approval" />
      <div className="min-w-0 flex-1">
        <p className="text-sm font-medium text-text-primary">
          Approval required
        </p>
        {resources && resources.length > 0 && (
          <p className="mt-0.5 text-caption text-text-secondary">
            {resources.length} resource{resources.length !== 1 ? "s" : ""} will be
            modified
          </p>
        )}
      </div>
      <div className="flex items-center gap-2">
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
                This will stop the remediation workflow. The work item will remain
                in its current state.
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
              disabled={isPending}
            >
              <Check size={14} />
              Approve
            </Button>
          </AlertDialogTrigger>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>Approve execution?</AlertDialogTitle>
              <AlertDialogDescription>
                The remediation will proceed with the proposed changes. This
                action cannot be undone.
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
  );
}
