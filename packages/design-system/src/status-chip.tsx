import type { WorkItemStatus } from "@pinky/contracts";

export interface StatusChipProps {
  status: WorkItemStatus;
}

const LABELS: Record<WorkItemStatus, string> = {
  ready: "Ready",
  accepted: "Accepted",
  in_progress: "In Progress",
  blocked: "Blocked",
  waiting_for_approval: "Needs Approval",
  done: "Done",
};

export function StatusChip({ status }: StatusChipProps) {
  return <span data-status={status}>{LABELS[status]}</span>;
}
