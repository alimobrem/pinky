"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Brain } from "lucide-react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import type { PaginatedResponse } from "@pinky/contracts";
import { cn } from "@/lib/utils";
import { api } from "@/lib/api";
import { QUERY_KEYS } from "@/lib/constants";
import { useSSE } from "@/hooks/use-sse";
import { NAV_ITEMS } from "@/components/shell/nav-config";
import { ScrollArea } from "@/components/ui/scroll-area";

export function Sidebar() {
  const pathname = usePathname();
  const qc = useQueryClient();

  useSSE("/api/v1/streams/events", {
    onEvent: {
      update: () => {
        qc.invalidateQueries({ queryKey: QUERY_KEYS.tasks({ status: "ready" }) });
        qc.invalidateQueries({ queryKey: QUERY_KEYS.issues({ status: "open" }) });
      },
    },
  });

  const { data: taskData } = useQuery({
    queryKey: QUERY_KEYS.tasks({ status: "ready" }),
    queryFn: () =>
      api.get<PaginatedResponse<unknown>>("/api/v1/work-items?status=ready&limit=1"),
    staleTime: 30_000,
  });

  const { data: issueData } = useQuery({
    queryKey: QUERY_KEYS.issues({ status: "open" }),
    queryFn: () =>
      api.get<PaginatedResponse<unknown>>("/api/v1/issues?status=open&limit=1"),
    staleTime: 30_000,
  });

  const taskCount = taskData?.total_count ?? 0;
  const issueCount = issueData?.total_count ?? 0;

  const badges: Record<string, number> = {};
  if (taskCount > 0) badges.tasks = taskCount;
  if (issueCount > 0) badges.watch = issueCount;

  return (
    <aside className="hidden h-full w-[200px] shrink-0 flex-col border-r border-border-default bg-bg-inset md:flex">
      <div className="flex items-center gap-2.5 px-5 py-5">
        <Brain size={20} className="text-brand-purple" />
        <span className="bg-gradient-to-r from-brand-pink to-brand-purple bg-clip-text text-sm font-bold tracking-widest text-transparent">
          PINKY
        </span>
      </div>

      <div className="mx-4 h-px bg-border-subtle" />

      <ScrollArea className="flex-1">
        <div className="space-y-1 px-3 py-3">
          <div className="px-2 pb-2 text-caption font-semibold uppercase tracking-widest text-text-tertiary">
            Workbench
          </div>
          {NAV_ITEMS.filter((i) => i.section === "primary").map((item) => {
            const active = pathname.startsWith(item.path);
            const Icon = item.icon;
            const badge = badges[item.id];

            return (
              <Link
                key={item.id}
                href={item.path}
                aria-current={active ? "page" : undefined}
                className={cn(
                  "group relative flex items-center gap-2.5 rounded-lg px-3 py-2 text-body-sm font-medium no-underline transition-all duration-150 focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none",
                  active
                    ? "bg-bg-active text-text-primary"
                    : "text-text-secondary hover:bg-bg-hover hover:text-text-primary",
                )}
              >
                {active && (
                  <div className="absolute -left-3 top-1/2 h-5 w-[3px] -translate-y-1/2 rounded-r-full bg-brand-pink" />
                )}
                <Icon
                  size={16}
                  strokeWidth={active ? 2 : 1.5}
                  className={cn(
                    "shrink-0",
                    active ? "text-brand-pink" : "text-text-tertiary",
                  )}
                />
                <span className="flex-1">{item.label}</span>
                {badge != null && badge > 0 && (
                  <span className="min-w-5 rounded-md bg-brand-pink/15 px-1.5 py-0.5 text-center font-mono text-caption font-semibold tabular-nums text-brand-pink">
                    {badge > 99 ? "99+" : badge}
                  </span>
                )}
              </Link>
            );
          })}
        </div>

        <div className="mx-4 h-px bg-border-subtle" />

        <div className="space-y-1 px-3 py-3">
          <div className="px-2 pb-2 text-caption font-semibold uppercase tracking-widest text-text-tertiary">
            System
          </div>
          {NAV_ITEMS.filter((i) => i.section === "secondary").map((item) => {
            const active = pathname.startsWith(item.path);
            const Icon = item.icon;

            return (
              <Link
                key={item.id}
                href={item.path}
                aria-current={active ? "page" : undefined}
                className={cn(
                  "flex items-center gap-2.5 rounded-lg px-3 py-2 text-body-sm font-medium no-underline transition-all duration-150 focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none",
                  active
                    ? "bg-bg-active text-text-primary"
                    : "text-text-secondary hover:bg-bg-hover hover:text-text-primary",
                )}
              >
                <Icon
                  size={16}
                  strokeWidth={active ? 2 : 1.5}
                  className={cn(
                    "shrink-0",
                    active ? "text-brand-pink" : "text-text-tertiary",
                  )}
                />
                <span className="flex-1">{item.label}</span>
              </Link>
            );
          })}
        </div>
      </ScrollArea>
    </aside>
  );
}
