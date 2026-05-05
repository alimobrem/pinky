"use client";

import { cn } from "@/lib/utils";
import {
  WORK_ITEM_STATUS,
  ISSUE_STATUS,
  EXECUTION_STATUS,
} from "@/lib/status";
import type {
  WorkItemStatus,
  IssueStatus,
  ExecutionStatus,
} from "@pinky/contracts";

type AnyStatus = WorkItemStatus | IssueStatus | ExecutionStatus;

function getConfig(status: AnyStatus) {
  if (status in WORK_ITEM_STATUS) return WORK_ITEM_STATUS[status as WorkItemStatus];
  if (status in ISSUE_STATUS) return ISSUE_STATUS[status as IssueStatus];
  if (status in EXECUTION_STATUS) return EXECUTION_STATUS[status as ExecutionStatus];
  return null;
}

interface StatusIndicatorProps {
  status: AnyStatus;
  size?: "sm" | "md";
  showLabel?: boolean;
  showIcon?: boolean;
  className?: string;
}

export function StatusIndicator({
  status,
  size = "sm",
  showLabel = true,
  showIcon = true,
  className,
}: StatusIndicatorProps) {
  const config = getConfig(status);
  if (!config) return null;

  const Icon = config.icon;
  const iconSize = size === "sm" ? 12 : 14;

  return (
    <span className={cn("inline-flex items-center gap-1.5", className)}>
      {showIcon && (
        <Icon size={iconSize} className={cn("shrink-0", config.color)} />
      )}
      {showLabel && (
        <span className={cn("text-xs font-medium", config.color)}>
          {config.label}
        </span>
      )}
    </span>
  );
}

interface StatusDotProps {
  status: AnyStatus;
  pulse?: boolean;
  className?: string;
}

export function StatusDot({ status, pulse, className }: StatusDotProps) {
  const config = getConfig(status);
  if (!config) return null;

  return (
    <span
      className={cn(
        "inline-block h-2 w-2 rounded-full",
        config.dot,
        pulse && "motion-safe:animate-pulse-dot",
        className,
      )}
      aria-label={config.label}
    />
  );
}
