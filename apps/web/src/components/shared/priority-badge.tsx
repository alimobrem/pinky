"use client";

import { cn } from "@/lib/utils";
import { PRIORITY } from "@/lib/status";
import {
  AlertTriangle,
  ArrowUp,
  Minus,
  ArrowDown,
} from "lucide-react";

const PRIORITY_ICONS = {
  critical: AlertTriangle,
  high: ArrowUp,
  medium: Minus,
  low: ArrowDown,
} as const;

interface PriorityBadgeProps {
  priority: string;
  size?: "sm" | "md";
  className?: string;
}

export function PriorityBadge({
  priority,
  size = "sm",
  className,
}: PriorityBadgeProps) {
  const config = PRIORITY[priority];
  if (!config) return null;

  const Icon = PRIORITY_ICONS[priority as keyof typeof PRIORITY_ICONS];
  const iconSize = size === "sm" ? 11 : 13;

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-md font-medium",
        size === "sm" ? "px-1.5 py-0.5 text-caption" : "px-2 py-1 text-xs",
        config.bg,
        config.color,
        config.pulse && "motion-safe:animate-pulse-dot",
        className,
      )}
    >
      {Icon && <Icon size={iconSize} className="shrink-0" />}
      {config.label}
    </span>
  );
}
