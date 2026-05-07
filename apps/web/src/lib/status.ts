import type { LucideIcon } from "lucide-react";
import {
  Circle,
  Loader,
  Ban,
  ShieldAlert,
  CheckCircle2,
  AlertTriangle,
  Search,
  CheckCheck,
  XCircle,
  EyeOff,
  Play,
  Clock,
  Timer,
  Slash,
} from "lucide-react";
import type {
  WorkItemStatus,
  IssueStatus,
  ExecutionStatus,
} from "@pinky/contracts";

interface StatusConfig {
  label: string;
  icon: LucideIcon;
  color: string;
  bg: string;
  border: string;
  dot: string;
}

export const WORK_ITEM_STATUS: Record<WorkItemStatus, StatusConfig> = {
  ready: {
    label: "Ready",
    icon: Circle,
    color: "text-status-ready",
    bg: "bg-status-ready/10",
    border: "border-l-status-ready",
    dot: "bg-status-ready",
  },
  in_progress: {
    label: "In Progress",
    icon: Loader,
    color: "text-status-in-progress",
    bg: "bg-status-in-progress/10",
    border: "border-l-status-in-progress",
    dot: "bg-status-in-progress",
  },
  blocked: {
    label: "Blocked",
    icon: Ban,
    color: "text-status-blocked",
    bg: "bg-status-blocked/10",
    border: "border-l-status-blocked",
    dot: "bg-status-blocked",
  },
  waiting_for_approval: {
    label: "Needs Approval",
    icon: ShieldAlert,
    color: "text-status-approval",
    bg: "bg-status-approval/10",
    border: "border-l-status-approval",
    dot: "bg-status-approval",
  },
  done: {
    label: "Done",
    icon: CheckCircle2,
    color: "text-status-done",
    bg: "bg-status-done/10",
    border: "border-l-status-done",
    dot: "bg-status-done",
  },
};

export const ISSUE_STATUS: Record<IssueStatus, StatusConfig> = {
  open: {
    label: "Open",
    icon: AlertTriangle,
    color: "text-status-blocked",
    bg: "bg-status-blocked/10",
    border: "border-l-status-blocked",
    dot: "bg-status-blocked",
  },
  investigating: {
    label: "Investigating",
    icon: Search,
    color: "text-status-in-progress",
    bg: "bg-status-in-progress/10",
    border: "border-l-status-in-progress",
    dot: "bg-status-in-progress",
  },
  resolved: {
    label: "Resolved",
    icon: CheckCheck,
    color: "text-status-done",
    bg: "bg-status-done/10",
    border: "border-l-status-done",
    dot: "bg-status-done",
  },
  suppressed: {
    label: "Suppressed",
    icon: EyeOff,
    color: "text-text-tertiary",
    bg: "bg-bg-hover",
    border: "border-l-text-tertiary",
    dot: "bg-text-tertiary",
  },
};

export const EXECUTION_STATUS: Record<ExecutionStatus, StatusConfig> = {
  pending: {
    label: "Pending",
    icon: Clock,
    color: "text-text-secondary",
    bg: "bg-bg-hover",
    border: "border-l-text-secondary",
    dot: "bg-text-secondary",
  },
  running: {
    label: "Running",
    icon: Play,
    color: "text-status-in-progress",
    bg: "bg-status-in-progress/10",
    border: "border-l-status-in-progress",
    dot: "bg-status-in-progress",
  },
  waiting_for_approval: {
    label: "Needs Approval",
    icon: ShieldAlert,
    color: "text-status-approval",
    bg: "bg-status-approval/10",
    border: "border-l-status-approval",
    dot: "bg-status-approval",
  },
  completed: {
    label: "Completed",
    icon: CheckCircle2,
    color: "text-status-done",
    bg: "bg-status-done/10",
    border: "border-l-status-done",
    dot: "bg-status-done",
  },
  failed: {
    label: "Failed",
    icon: XCircle,
    color: "text-status-blocked",
    bg: "bg-status-blocked/10",
    border: "border-l-status-blocked",
    dot: "bg-status-blocked",
  },
  timed_out: {
    label: "Timed Out",
    icon: Timer,
    color: "text-status-approval",
    bg: "bg-status-approval/10",
    border: "border-l-status-approval",
    dot: "bg-status-approval",
  },
  cancelled: {
    label: "Cancelled",
    icon: Slash,
    color: "text-text-tertiary",
    bg: "bg-bg-hover",
    border: "border-l-text-tertiary",
    dot: "bg-text-tertiary",
  },
};

interface PriorityConfig {
  label: string;
  color: string;
  bg: string;
  border: string;
  pulse: boolean;
}

export const PRIORITY: Record<string, PriorityConfig> = {
  critical: {
    label: "Critical",
    color: "text-priority-critical",
    bg: "bg-priority-critical/15",
    border: "border-priority-critical",
    pulse: true,
  },
  high: {
    label: "High",
    color: "text-priority-high",
    bg: "bg-priority-high/15",
    border: "border-priority-high",
    pulse: false,
  },
  medium: {
    label: "Medium",
    color: "text-priority-medium",
    bg: "bg-priority-medium/15",
    border: "border-priority-medium",
    pulse: false,
  },
  low: {
    label: "Low",
    color: "text-priority-low",
    bg: "bg-priority-low/15",
    border: "border-priority-low",
    pulse: false,
  },
};

export const SEVERITY: Record<string, PriorityConfig> = {
  critical: PRIORITY.critical,
  high: PRIORITY.high,
  medium: PRIORITY.medium,
  low: PRIORITY.low,
  info: {
    label: "Info",
    color: "text-status-ready",
    bg: "bg-status-ready/10",
    border: "border-status-ready",
    pulse: false,
  },
};

export function confidenceColor(c: number): string {
  if (c >= 0.8) return "text-status-done";
  if (c >= 0.5) return "text-status-in-progress";
  return "text-status-blocked";
}

export function confidenceLabel(c: number): string {
  if (c >= 0.8) return "High";
  if (c >= 0.5) return "Moderate";
  return "Low";
}
