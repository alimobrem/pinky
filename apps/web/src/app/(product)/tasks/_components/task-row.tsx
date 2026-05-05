"use client";

import type { WorkItem } from "@pinky/contracts";
import { StatusIndicator } from "@/components/shared/status-indicator";
import { PriorityBadge } from "@/components/shared/priority-badge";
import { ConfidenceBadge } from "@/components/shared/confidence-badge";
import { RelativeTime } from "@/components/shared/relative-time";

interface TaskRowProps {
  task: WorkItem;
  clusterName?: string;
}

export function taskColumns(clusterMap: Record<string, string>) {
  return [
    {
      id: "title",
      header: "Task",
      cell: (task: WorkItem) => (
        <div className="min-w-0">
          <p className="truncate text-sm font-medium text-text-primary">
            {task.title}
          </p>
          {clusterMap[task.cluster_id] && (
            <p className="mt-0.5 truncate font-mono text-[11px] text-text-tertiary">
              {clusterMap[task.cluster_id]}
            </p>
          )}
        </div>
      ),
      className: "max-w-[400px]",
    },
    {
      id: "priority",
      header: "Priority",
      sortable: true,
      cell: (task: WorkItem) => <PriorityBadge priority={task.priority} />,
      className: "w-24",
    },
    {
      id: "status",
      header: "Status",
      sortable: true,
      cell: (task: WorkItem) => <StatusIndicator status={task.status} />,
      className: "w-32",
    },
    {
      id: "confidence",
      header: "Conf.",
      sortable: true,
      cell: (task: WorkItem) => <ConfidenceBadge value={task.confidence} />,
      className: "w-16 text-right",
      headerClassName: "text-right",
    },
    {
      id: "age",
      header: "Age",
      sortable: true,
      cell: (task: WorkItem) => <RelativeTime date={task.created_at} />,
      className: "w-28 text-right",
      headerClassName: "text-right",
    },
  ];
}

export function TaskRowCard({ task, clusterName }: TaskRowProps) {
  return (
    <div className="space-y-2 rounded-lg border border-border-subtle bg-bg-surface px-4 py-3 transition-colors hover:border-border-default">
      <div className="flex items-start justify-between gap-2">
        <p className="text-sm font-medium text-text-primary">{task.title}</p>
        <PriorityBadge priority={task.priority} />
      </div>
      <div className="flex items-center gap-3">
        <StatusIndicator status={task.status} />
        <ConfidenceBadge value={task.confidence} />
        {clusterName && (
          <span className="font-mono text-[11px] text-text-tertiary">
            {clusterName}
          </span>
        )}
        <RelativeTime date={task.created_at} className="ml-auto" />
      </div>
    </div>
  );
}
