"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { LayoutDashboard, CheckSquare, Eye, Clock, AlertTriangle, Settings, Brain } from "lucide-react";
import type { ComponentType } from "react";
import { cn } from "@/lib/utils";
import { api } from "@/lib/api";

interface NavItem {
  id: string;
  label: string;
  path: string;
  icon: ComponentType<{ size?: number; strokeWidth?: number; className?: string }>;
  section: "primary" | "secondary";
}

const NAV_ITEMS: NavItem[] = [
  { id: "dashboard", label: "Dashboard", path: "/dashboard", icon: LayoutDashboard, section: "primary" },
  { id: "tasks", label: "Tasks", path: "/tasks", icon: CheckSquare, section: "primary" },
  { id: "watch", label: "Watch", path: "/watch", icon: Eye, section: "primary" },
  { id: "history", label: "History", path: "/history", icon: Clock, section: "primary" },
  { id: "alerts", label: "Alerts", path: "/alerts", icon: AlertTriangle, section: "primary" },
  { id: "settings", label: "Settings", path: "/settings", icon: Settings, section: "secondary" },
];

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
    <nav className="w-[220px] min-h-screen bg-sidebar border-r border-sidebar-border flex flex-col max-xl:w-[56px] max-md:hidden">
      {/* Brand */}
      <div className="px-5 pt-5 pb-6 flex items-center gap-3">
        <div className="relative">
          <Brain size={24} className="text-accent-brain drop-shadow-[0_0_8px_rgba(167,139,250,0.4)]" />
          {brainActive && <span className="absolute -top-0.5 -right-0.5 w-2 h-2 rounded-full bg-status-done animate-brain-pulse" />}
        </div>
        <span className="text-[17px] font-bold tracking-[0.1em] bg-gradient-to-r from-accent-brand to-accent-brain bg-clip-text text-transparent max-xl:hidden">PINKY</span>
      </div>

      <div className="mx-4 mb-3 h-px bg-border-subtle" />

      {/* Primary nav */}
      <div className="flex flex-col gap-1 px-3 max-xl:px-1.5">
        {NAV_ITEMS.filter(i => i.section === "primary").map(item => (
          <NavLink key={item.id} item={item} active={pathname.startsWith(item.path)} badge={badges[item.id]} />
        ))}
      </div>

      <div className="flex-1" />
      <div className="mx-4 my-3 h-px bg-border-subtle" />

      {/* Secondary nav */}
      <div className="flex flex-col gap-1 px-3 pb-5 max-xl:px-1.5">
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
        "group relative flex items-center gap-3 px-3 py-2.5 rounded-lg text-[13px] font-medium no-underline transition-all duration-150",
        active
          ? "text-text-primary bg-bg-elevated shadow-card"
          : "text-text-secondary hover:text-text-primary hover:bg-bg-hover"
      )}
    >
      {active && <div className="absolute left-0 top-1/2 -translate-y-1/2 w-[3px] h-5 rounded-r-full bg-accent-brand" />}
      <Icon size={18} strokeWidth={active ? 2 : 1.6} className={cn("shrink-0", active ? "text-accent-brand" : "text-text-tertiary group-hover:text-text-secondary")} />
      <span className="flex-1 max-xl:hidden">{item.label}</span>
      {badge != null && badge !== "0" && (
        <span className="text-xs font-mono font-semibold tabular bg-accent-brand/15 text-accent-brand px-1.5 py-0.5 rounded min-w-[20px] text-center max-xl:hidden">{badge}</span>
      )}
    </Link>
  );
}
