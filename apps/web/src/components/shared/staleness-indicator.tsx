"use client";

import { cn } from "@/lib/utils";
import { Wifi, WifiOff } from "lucide-react";
import type { SSEConnectionState } from "@/hooks/use-sse";

interface StalenessIndicatorProps {
  state: SSEConnectionState;
  lastUpdated: Date | null;
  className?: string;
}

export function StalenessIndicator({
  state,
  className,
}: StalenessIndicatorProps) {
  const isLive = state === "connected";

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 text-[11px]",
        isLive ? "text-status-done" : "text-text-tertiary",
        className,
      )}
    >
      {isLive ? (
        <Wifi size={12} className="text-status-done" />
      ) : (
        <WifiOff size={12} className="text-text-tertiary" />
      )}
      {isLive ? "Live" : state === "reconnecting" ? "Reconnecting..." : "Disconnected"}
    </span>
  );
}
