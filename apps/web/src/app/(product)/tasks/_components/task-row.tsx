"use client";

import type { WorkItem } from "@pinky/contracts";
import type { Column } from "@/components/shared/data-table";
import { StatusIndicator } from "@/components/shared/status-indicator";
import { PriorityBadge } from "@/components/shared/priority-badge";
import { ConfidenceBadge } from "@/components/shared/confidence-badge";
import { RelativeTime } from "@/components/shared/relative-time";

const PRIORITY_ORDER: Record<string, number> = { critical: 0, high: 1, medium: 2, low: 3 };
const STATUS_ORDER: Record<string, number> = {
  ready: 0, in_progress: 1, blocked: 2, waiting_for_approval: 3, done: 4,
};

interface TaskRowProps {
  task: WorkItem;
  clusterName?: string;
}

export function taskColumns(): Column<WorkItem>[] {
  return [
    {
      id: "title",
      header: "Task",
      cell: (task: WorkItem) => (
        <div className="min-w-0">
          <p className="truncate text-sm font-medium text-text-primary">
            {task.title}
          </p>
          <div className="mt-0.5 flex items-center gap-2 truncate font-mono text-caption text-text-tertiary">
            {task.cluster_display_name && (
              <span>{task.cluster_display_name}</span>
            )}
            {task.owner_display_name && (
              <span className="truncate">{task.owner_display_name}</span>
            )}
          </div>
        </div>
      ),
      className: "max-w-[400px]",
    },
    {
      id: "priority",
      header: "Priority",
      sortable: true,
      sortValue: (task) => PRIORITY_ORDER[task.priority] ?? 99,
      cell: (task) => <PriorityBadge priority={task.priority} />,
      className: "w-24",
    },
    {
      id: "status",
      header: "Status",
      sortable: true,
      sortValue: (task) => STATUS_ORDER[task.status] ?? 99,
      cell: (task) => <StatusIndicator status={task.status} />,
      className: "w-32",
    },
    {
      id: "confidence",
      header: "Confidence",
      sortable: true,
      sortValue: (task) => task.confidence ?? 0,
      cell: (task) => <ConfidenceBadge value={task.confidence} />,
      className: "w-16 text-right",
      headerClassName: "text-right",
    },
    {
      id: "age",
      header: "Age",
      sortable: true,
      sortValue: (task) => new Date(task.created_at).getTime(),
      cell: (task) => <RelativeTime date={task.created_at} />,
      className: "w-28 text-right",
      headerClassName: "text-right",
    },
  ];
}

export function TaskRowCard({ task, clusterName }: TaskRowProps) {
  return (
    <div className="space-y-2 rounded-lg border border-border-default bg-bg-surface px-4 py-3 transition-colors hover:border-border-strong">
      <div className="flex items-start justify-between gap-2">
        <p className="text-sm font-medium text-text-primary">{task.title}</p>
        <PriorityBadge priority={task.priority} />
      </div>
      <div className="flex items-center gap-3">
        <StatusIndicator status={task.status} />
        <ConfidenceBadge value={task.confidence} />
        {clusterName && (
          <span className="font-mono text-caption text-text-tertiary">
            {clusterName}
          </span>
        )}
        {task.owner_display_name && (
          <span className="font-mono text-caption text-text-tertiary truncate">
            {task.owner_display_name}
          </span>
        )}
        <RelativeTime date={task.created_at} className="ml-auto" />
      </div>
    </div>
  );
}
