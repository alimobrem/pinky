"use client";

import type { WorkItem } from "@pinky/contracts";
import { cn } from "@/lib/utils";
import { StatusIndicator } from "@/components/shared/status-indicator";
import { PriorityBadge } from "@/components/shared/priority-badge";
import { ConfidenceBadge } from "@/components/shared/confidence-badge";
import { RelativeTime } from "@/components/shared/relative-time";
import { Button } from "@/components/ui/button";
import { ArrowRight } from "lucide-react";
import Link from "next/link";

interface TaskPreviewProps {
  task: WorkItem | null;
  clusterName?: string;
  className?: string;
}

export function TaskPreview({ task, clusterName, className }: TaskPreviewProps) {
  if (!task) {
    return (
      <div
        className={cn(
          "flex items-center justify-center rounded-lg border border-border-default bg-bg-surface p-8 text-sm text-text-tertiary",
          className,
        )}
      >
        Select a task to preview
      </div>
    );
  }

  return (
    <div
      className={cn(
        "space-y-4 rounded-lg border border-border-default bg-bg-surface p-4",
        className,
      )}
    >
      <div className="space-y-2">
        <div className="flex items-center gap-2">
          <PriorityBadge priority={task.priority} />
          <StatusIndicator status={task.status} />
        </div>
        <h3 className="text-sm font-semibold text-text-primary">{task.title}</h3>
        {clusterName && (
          <p className="font-mono text-[11px] text-text-tertiary">{clusterName}</p>
        )}
      </div>

      {task.why_now && (
        <div className="space-y-1">
          <p className="text-[11px] font-semibold uppercase tracking-wider text-text-tertiary">
            Why now
          </p>
          <p className="text-[13px] leading-relaxed text-text-secondary">
            {task.why_now}
          </p>
        </div>
      )}

      {task.recommended_next_step && (
        <div className="space-y-1">
          <p className="text-[11px] font-semibold uppercase tracking-wider text-text-tertiary">
            Recommended
          </p>
          <p className="text-[13px] leading-relaxed text-text-secondary">
            {task.recommended_next_step}
          </p>
        </div>
      )}

      <div className="flex items-center gap-3 text-[11px] text-text-tertiary">
        <ConfidenceBadge value={task.confidence} />
        <RelativeTime date={task.created_at} />
      </div>

      <Link href={`/tasks/${task.id}`} className="no-underline">
        <Button size="sm" className="w-full gap-1">
          Open <ArrowRight size={14} />
        </Button>
      </Link>
    </div>
  );
}
