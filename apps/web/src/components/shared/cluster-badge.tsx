"use client";

import { cn } from "@/lib/utils";
import { Server } from "lucide-react";

interface ClusterBadgeProps {
  name: string;
  className?: string;
}

export function ClusterBadge({ name, className }: ClusterBadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-md bg-bg-hover px-1.5 py-0.5 font-mono text-[11px] text-text-secondary",
        className,
      )}
    >
      <Server size={10} className="shrink-0 text-text-tertiary" />
      {name}
    </span>
  );
}
