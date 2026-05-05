"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Brain, PanelLeftClose } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import type { PaginatedResponse } from "@pinky/contracts";
import { cn } from "@/lib/utils";
import { api } from "@/lib/api";
import { QUERY_KEYS } from "@/lib/constants";
import { NAV_ITEMS } from "@/components/shell/nav-config";
import { Button } from "@/components/ui/button";
import { Kbd } from "@/components/shared/keyboard-shortcut-hint";
import { ScrollArea } from "@/components/ui/scroll-area";

interface DetailPanelProps {
  isOpen: boolean;
  onClose: () => void;
}

export function DetailPanel({ isOpen, onClose }: DetailPanelProps) {
  const pathname = usePathname();

  const { data: taskData } = useQuery({
    queryKey: QUERY_KEYS.tasks({ status: "ready" }),
    queryFn: () =>
      api.get<PaginatedResponse<unknown>>("/api/v1/work-items?status=ready&limit=1"),
    staleTime: 30_000,
    refetchInterval: 60_000,
  });

  const { data: issueData } = useQuery({
    queryKey: ["issues", { status: "open" }],
    queryFn: () =>
      api.get<PaginatedResponse<unknown>>("/api/v1/issues?status=open&limit=1"),
    staleTime: 30_000,
    refetchInterval: 60_000,
  });

  const taskCount = taskData?.total_count ?? 0;
  const issueCount = issueData?.total_count ?? 0;

  if (!isOpen) return null;

  return (
    <aside className="hidden h-full w-[220px] shrink-0 border-r border-border-subtle bg-bg-inset xl:flex xl:flex-col">
      <div className="flex items-center justify-between px-4 py-4">
        <div className="flex items-center gap-2">
          <Brain size={16} className="text-brand-purple" />
          <span className="bg-gradient-to-r from-brand-pink to-brand-purple bg-clip-text text-sm font-bold tracking-wider text-transparent">
            PINKY
          </span>
        </div>
        <Button
          variant="ghost"
          size="icon"
          className="h-6 w-6 text-text-tertiary hover:text-text-secondary"
          onClick={onClose}
          aria-label="Close panel"
        >
          <PanelLeftClose size={14} />
        </Button>
      </div>

      <div className="mx-4 h-px bg-border-subtle" />

      <ScrollArea className="flex-1">
        <div className="space-y-1 px-3 py-3">
          <div className="px-2 pb-1 text-[10px] font-semibold uppercase tracking-widest text-text-tertiary">
            Workbench
          </div>
          {NAV_ITEMS.filter((i) => i.section === "primary").map((item) => {
            const active = pathname.startsWith(item.path);
            const Icon = item.icon;
            const badge =
              item.id === "tasks" ? taskCount : item.id === "watch" ? issueCount : 0;

            return (
              <Link
                key={item.id}
                href={item.path}
                aria-current={active ? "page" : undefined}
                className={cn(
                  "flex items-center gap-2.5 rounded-lg px-2.5 py-2 text-[13px] font-medium no-underline transition-all duration-150",
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
                {badge > 0 && (
                  <span className="min-w-5 rounded-md bg-brand-pink/15 px-1.5 py-0.5 text-center font-mono text-[10px] font-semibold tabular text-brand-pink">
                    {badge}
                  </span>
                )}
                {item.shortcut && (
                  <Kbd keys={item.shortcut} className="opacity-0 transition-opacity group-hover:opacity-100" />
                )}
              </Link>
            );
          })}
        </div>

        <div className="mx-4 h-px bg-border-subtle" />

        <div className="space-y-1 px-3 py-3">
          <div className="px-2 pb-1 text-[10px] font-semibold uppercase tracking-widest text-text-tertiary">
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
                  "flex items-center gap-2.5 rounded-lg px-2.5 py-2 text-[13px] font-medium no-underline transition-all duration-150",
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
