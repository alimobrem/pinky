export const STATUS_BG: Record<string, string> = {
  ready: "bg-status-ready",
  accepted: "bg-status-accepted",
  in_progress: "bg-status-in-progress",
  blocked: "bg-status-blocked",
  waiting_for_approval: "bg-status-approval",
  done: "bg-status-done",
};

export const STATUS_BORDER: Record<string, string> = {
  ready: "border-l-status-ready",
  accepted: "border-l-status-accepted",
  in_progress: "border-l-status-in-progress",
  blocked: "border-l-status-blocked",
  waiting_for_approval: "border-l-status-approval",
  done: "border-l-status-done",
};

export const PRIORITY_BG: Record<string, string> = {
  critical: "bg-priority-critical",
  high: "bg-priority-high",
  medium: "bg-priority-medium",
  low: "bg-priority-low",
};

export const SEVERITY_VARIANT: Record<string, "default" | "secondary" | "destructive" | "outline"> = {
  critical: "destructive",
  high: "destructive",
  medium: "secondary",
  low: "outline",
  info: "outline",
};

export const SEVERITY_BORDER: Record<string, string> = {
  critical: "border-l-priority-critical",
  high: "border-l-priority-high",
  medium: "border-l-priority-medium",
  low: "border-l-priority-low",
  info: "border-l-status-ready",
};

export function confColor(c: number): string {
  return c >= 0.8 ? "text-status-done" : c >= 0.5 ? "text-status-in-progress" : "text-status-blocked";
}

export function confLabel(c: number): string {
  return c >= 0.8 ? "High confidence" : c >= 0.5 ? "Moderate confidence" : "Low confidence";
}
