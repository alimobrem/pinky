"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { Brain } from "lucide-react";
import { cn } from "@/lib/utils";
import { api } from "@/lib/api";
import { NAV_ITEMS, type NavItem } from "@/components/nav-config";

export function NavRail() {
  const pathname = usePathname();
  const [badges, setBadges] = useState<Record<string, string>>({});
  const [brainActive, setBrainActive] = useState(false);

  useEffect(() => {
    const fetchBadges = () => {
      api.get<{ items: unknown[]; has_more: boolean; total_count?: number }>("/api/v1/work-items?status=ready&limit=1")
        .then(d => { const count = d.total_count ?? (d.items || []).length; setBadges(prev => ({ ...prev, tasks: `${count}` })); })
        .catch(() => {});
      api.get<{ items: unknown[]; has_more: boolean; total_count?: number }>("/api/v1/alerts?limit=1")
        .then(d => { const count = d.total_count ?? (d.items || []).length; setBadges(prev => ({ ...prev, alerts: `${count}` })); })
        .catch(() => {});
      api.get<{ items: unknown[]; total_count?: number }>("/api/v1/issues?status=open&limit=1")
        .then(d => setBrainActive((d.total_count ?? (d.items || []).length) > 0))
        .catch(() => {});
    };
    fetchBadges();
    const interval = setInterval(fetchBadges, 30000);
    return () => clearInterval(interval);
  }, []);

  return (
    <nav className="hidden h-screen shrink-0 overflow-y-auto border-r border-sidebar-border bg-[linear-gradient(180deg,#0b0a12_0%,#09080f_100%)] md:flex md:w-[96px] md:flex-col xl:w-[248px]">
      {/* Brand */}
      <div className="flex items-center gap-3 px-4 pb-6 pt-5 xl:px-5">
        <div className="relative">
          <Brain size={24} className="text-accent-brain drop-shadow-[0_0_8px_rgba(167,139,250,0.4)]" />
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

      {/* Primary nav */}
      <div className="flex flex-col gap-1 px-2 xl:px-3">
        <div className="hidden px-2 pb-2 text-xs font-semibold uppercase tracking-[0.18em] text-text-tertiary xl:block">
          Workbench
        </div>
        {NAV_ITEMS.filter(i => i.section === "primary").map(item => (
          <NavLink key={item.id} item={item} active={pathname.startsWith(item.path)} badge={badges[item.id]} />
        ))}
      </div>

      <div className="mx-4 mb-4 mt-6 h-px bg-border-subtle" />

      {/* Secondary nav */}
      <div className="flex flex-col gap-1 px-2 pb-6 xl:px-3">
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
        "group relative flex items-center gap-3 rounded-xl px-3 py-3 text-[13px] font-medium no-underline transition-all duration-150",
        active
          ? "bg-bg-elevated text-text-primary shadow-card"
          : "text-text-secondary hover:bg-bg-hover hover:text-text-primary"
      )}
    >
      {active && <div className="absolute left-0 top-1/2 -translate-y-1/2 w-[3px] h-5 rounded-r-full bg-accent-brand" />}
      <Icon size={18} strokeWidth={active ? 2 : 1.6} className={cn("shrink-0", active ? "text-accent-brand" : "text-text-tertiary group-hover:text-text-secondary")} />
      <span className="hidden flex-1 xl:block">{item.label}</span>
      {badge != null && badge !== "0" && (
        <>
          <span className="hidden min-w-[20px] rounded bg-accent-brand/15 px-1.5 py-0.5 text-center font-mono text-xs font-semibold tabular text-accent-brand xl:block">{badge}</span>
          <span className="absolute right-2 top-2 h-2 w-2 rounded-full bg-accent-brand xl:hidden" />
        </>
      )}
    </Link>
  );
}
