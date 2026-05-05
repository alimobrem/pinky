"use client";

import { cn } from "@/lib/utils";
import { confidenceColor, confidenceLabel } from "@/lib/status";
import { percentLabel } from "@/lib/format";

interface ConfidenceBadgeProps {
  value: number | null;
  className?: string;
}

export function ConfidenceBadge({ value, className }: ConfidenceBadgeProps) {
  if (value === null || value === undefined) return null;

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 font-mono text-[11px] tabular-nums",
        confidenceColor(value),
        className,
      )}
      title={confidenceLabel(value)}
    >
      {percentLabel(value)}
    </span>
  );
}
