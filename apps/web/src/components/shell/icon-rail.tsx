"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Brain } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import type { PaginatedResponse } from "@pinky/contracts";
import { cn } from "@/lib/utils";
import { api } from "@/lib/api";
import { QUERY_KEYS } from "@/lib/constants";
import { NAV_ITEMS } from "@/components/shell/nav-config";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { Kbd } from "@/components/shared/keyboard-shortcut-hint";

export function IconRail() {
  const pathname = usePathname();

  const { data: taskData } = useQuery({
    queryKey: QUERY_KEYS.tasks({ status: "ready" }),
    queryFn: () =>
      api.get<PaginatedResponse<unknown>>("/api/v1/work-items?status=ready&limit=1"),
    staleTime: 30_000,
    refetchInterval: 60_000,
  });

  const taskCount = taskData?.total_count ?? 0;

  return (
    <TooltipProvider delayDuration={200}>
      <nav className="hidden h-full w-14 shrink-0 flex-col items-center border-r border-border-subtle bg-bg-inset py-4 md:flex">
        <Link
          href="/dashboard"
          className="group mb-6 flex items-center justify-center no-underline"
          aria-label="Pinky Home"
        >
          <Brain
            size={22}
            className="text-brand-purple transition-all duration-200 group-hover:drop-shadow-[0_0_12px_rgba(167,139,250,0.5)]"
          />
        </Link>

        <div className="flex flex-1 flex-col gap-1">
          {NAV_ITEMS.filter((i) => i.section === "primary").map((item) => {
            const active = pathname.startsWith(item.path);
            const Icon = item.icon;
            const badge = item.id === "tasks" && taskCount > 0 ? taskCount : null;

            return (
              <Tooltip key={item.id}>
                <TooltipTrigger asChild>
                  <Link
                    href={item.path}
                    aria-label={item.label}
                    aria-current={active ? "page" : undefined}
                    className={cn(
                      "relative flex h-10 w-10 items-center justify-center rounded-lg no-underline transition-all duration-150",
                      active
                        ? "bg-bg-active text-text-primary"
                        : "text-text-tertiary hover:bg-bg-hover hover:text-text-secondary",
                    )}
                  >
                    {active && (
                      <div className="absolute -left-[7px] top-1/2 h-5 w-[3px] -translate-y-1/2 rounded-r-full bg-brand-pink" />
                    )}
                    <Icon size={18} strokeWidth={active ? 2 : 1.5} />
                    {badge !== null && (
                      <span className="absolute -right-0.5 -top-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-brand-pink px-1 font-mono text-[9px] font-bold text-text-inverse">
                        {badge > 99 ? "99+" : badge}
                      </span>
                    )}
                  </Link>
                </TooltipTrigger>
                <TooltipContent side="right" className="flex items-center gap-2">
                  {item.label}
                  {item.shortcut && <Kbd keys={item.shortcut} />}
                </TooltipContent>
              </Tooltip>
            );
          })}
        </div>

        <div className="mt-auto flex flex-col gap-1">
          {NAV_ITEMS.filter((i) => i.section === "secondary").map((item) => {
            const active = pathname.startsWith(item.path);
            const Icon = item.icon;

            return (
              <Tooltip key={item.id}>
                <TooltipTrigger asChild>
                  <Link
                    href={item.path}
                    aria-label={item.label}
                    aria-current={active ? "page" : undefined}
                    className={cn(
                      "flex h-10 w-10 items-center justify-center rounded-lg no-underline transition-all duration-150",
                      active
                        ? "bg-bg-active text-text-primary"
                        : "text-text-tertiary hover:bg-bg-hover hover:text-text-secondary",
                    )}
                  >
                    <Icon size={18} strokeWidth={active ? 2 : 1.5} />
                  </Link>
                </TooltipTrigger>
                <TooltipContent side="right" className="flex items-center gap-2">
                  {item.label}
                  {item.shortcut && <Kbd keys={item.shortcut} />}
                </TooltipContent>
              </Tooltip>
            );
          })}
        </div>
      </nav>
    </TooltipProvider>
  );
}
