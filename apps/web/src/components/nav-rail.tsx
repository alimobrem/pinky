"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Brain } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import type { PaginatedResponse } from "@pinky/contracts";
import { cn } from "@/lib/utils";
import { api } from "@/lib/api";
import { NAV_ITEMS, type NavItem } from "@/components/nav-config";

export function NavRail() {
  const pathname = usePathname();

  const { data: taskData } = useQuery({
    queryKey: ["nav-badge-tasks"],
    queryFn: () => api.get<PaginatedResponse<unknown>>("/api/v1/work-items?status=ready&limit=1"),
    staleTime: 30_000,
    refetchInterval: 60_000,
  });

  const { data: issueData } = useQuery({
    queryKey: ["nav-badge-issues"],
    queryFn: () => api.get<PaginatedResponse<unknown>>("/api/v1/issues?status=open&limit=1"),
    staleTime: 30_000,
    refetchInterval: 60_000,
  });

  const taskCount = taskData?.total_count ?? taskData?.items?.length ?? 0;
  const brainActive = (issueData?.total_count ?? issueData?.items?.length ?? 0) > 0;

  const badges: Record<string, string> = {};
  if (taskCount > 0) badges.tasks = `${taskCount}`;

  return (
    <nav className="hidden h-screen shrink-0 overflow-y-auto border-r border-sidebar-border bg-[linear-gradient(180deg,#0e0c18_0%,#0a0912_100%)] md:flex md:w-[80px] md:flex-col xl:w-[260px]">
      <div className="flex items-center gap-3 px-4 pb-6 pt-6 xl:px-6">
        <div className="relative">
          <Brain size={24} className="text-accent-brain drop-shadow-[0_0_12px_rgba(167,139,250,0.5)] transition-all duration-300 hover:drop-shadow-[0_0_20px_rgba(167,139,250,0.7)]" />
          {brainActive && <span className="absolute -top-0.5 -right-0.5 w-2 h-2 rounded-full bg-status-done animate-brain-pulse" />}
        </div>
        <div className="hidden min-w-0 xl:block">
          <div className="bg-gradient-to-r from-accent-brand to-accent-brain bg-clip-text text-[17px] font-bold tracking-[0.1em] text-transparent">
            PINKY
          </div>
          <div className="mt-1 text-xs uppercase tracking-[0.16em] text-text-tertiary">
            Ops Inbox
          </div>
        </div>
      </div>

      <div className="mx-4 mb-4 h-px bg-border-subtle" />

      <div className="flex flex-col gap-1.5 px-3 xl:px-4">
        <div className="hidden px-2 pb-2 text-xs font-semibold uppercase tracking-[0.18em] text-text-tertiary xl:block">
          Workbench
        </div>
        {NAV_ITEMS.filter(i => i.section === "primary").map(item => (
          <NavLink key={item.id} item={item} active={pathname.startsWith(item.path)} badge={badges[item.id]} />
        ))}
      </div>

      <div className="mt-auto mx-4 mb-4 h-px bg-border-subtle" />

      <div className="flex flex-col gap-1.5 px-3 pb-6 xl:px-4">
        <div className="hidden px-2 pb-2 text-xs font-semibold uppercase tracking-[0.18em] text-text-tertiary xl:block">
          System
        </div>
        {NAV_ITEMS.filter(i => i.section === "secondary").map(item => (
          <NavLink key={item.id} item={item} active={pathname.startsWith(item.path)} />
        ))}
      </div>
    </nav>
  );
}

function NavLink({ item, active, badge }: { item: NavItem; active: boolean; badge?: string }) {
  const Icon = item.icon;
  return (
    <Link
      href={item.path}
      aria-label={item.label}
      aria-current={active ? "page" : undefined}
      className={cn(
        "group relative flex items-center justify-center gap-3 rounded-xl px-3.5 py-3 text-[13px] font-medium no-underline transition-all duration-200 xl:justify-start",
        active
          ? "bg-bg-elevated text-text-primary shadow-[0_0_16px_rgba(244,114,182,0.08),0_1px_3px_rgba(0,0,0,0.3)]"
          : "text-text-secondary hover:bg-bg-hover hover:text-text-primary hover:shadow-[0_0_12px_rgba(167,139,250,0.06)]"
      )}
    >
      {active && <div className="absolute left-0 top-1/2 -translate-y-1/2 w-[3px] h-6 rounded-r-full bg-accent-brand shadow-[0_0_8px_rgba(244,114,182,0.5)]" />}
      <Icon size={18} strokeWidth={active ? 2 : 1.6} className={cn("shrink-0 transition-colors duration-200", active ? "text-accent-brand" : "text-text-tertiary group-hover:text-text-secondary")} />
      <span className="hidden flex-1 xl:block">{item.label}</span>
      {badge != null && badge !== "0" && (
        <>
          <span className="hidden min-w-[20px] rounded-md bg-accent-brand/15 px-1.5 py-0.5 text-center font-mono text-xs font-semibold tabular text-accent-brand xl:block">{badge}</span>
          <span className="absolute right-1.5 top-1.5 h-2 w-2 rounded-full bg-accent-brand xl:hidden" />
        </>
      )}
    </Link>
  );
}
