"use client";

import { useState, useEffect } from "react";
import { cn } from "@/lib/utils";
import { relativeTime, fullDateTime } from "@/lib/format";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";

interface RelativeTimeProps {
  date: string;
  className?: string;
  live?: boolean;
}

export function RelativeTime({ date, className, live = true }: RelativeTimeProps) {
  const [display, setDisplay] = useState(() => relativeTime(date));

  useEffect(() => {
    if (!live) return;
    const timer = setInterval(() => setDisplay(relativeTime(date)), 30_000);
    return () => clearInterval(timer);
  }, [date, live]);

  return (
    <TooltipProvider delayDuration={300}>
      <Tooltip>
        <TooltipTrigger asChild>
          <time
            dateTime={date}
            className={cn("font-mono text-[11px] tabular text-text-tertiary", className)}
          >
            {display}
          </time>
        </TooltipTrigger>
        <TooltipContent side="top" className="text-xs">
          {fullDateTime(date)}
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}
