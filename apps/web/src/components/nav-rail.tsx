"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { CheckSquare, Eye, Clock, AlertTriangle, Settings, Brain } from "lucide-react";
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
      api.get<{ items: unknown[]; has_more: boolean }>("/api/v1/work-items?status=ready")
        .then(d => { const count = (d.items || []).length; setBadges(prev => ({ ...prev, tasks: d.has_more ? `${count}+` : `${count}` })); })
        .catch(() => {});
      api.get<{ items: unknown[]; has_more: boolean }>("/api/v1/alerts")
        .then(d => { const count = (d.items || []).length; setBadges(prev => ({ ...prev, alerts: d.has_more ? `${count}+` : `${count}` })); })
        .catch(() => {});
      api.get<{ items: unknown[] }>("/api/v1/issues?status=open")
        .then(d => setBrainActive((d.items || []).length > 0))
        .catch(() => {});
    };
    fetchBadges();
    const interval = setInterval(fetchBadges, 30000);
    return () => clearInterval(interval);
  }, []);

  return (
    <nav className="w-[200px] min-h-screen bg-sidebar border-r border-sidebar-border flex flex-col max-xl:w-14 max-md:hidden relative overflow-hidden">
      {/* Subtle gradient glow at top */}
      <div className="absolute top-0 left-0 right-0 h-32 bg-gradient-to-b from-accent-brain/[0.04] to-transparent pointer-events-none" />

      <div className="px-4 pt-5 pb-6 flex items-center gap-2.5 relative">
        <div className="relative">
          <Brain size={24} className="text-accent-brain" />
          {brainActive && <span className="absolute -top-0.5 -right-0.5 w-2 h-2 rounded-full bg-status-done animate-brain-pulse" />}
        </div>
        <span className="text-lg font-bold tracking-[0.08em] bg-gradient-to-br from-accent-brand to-accent-brain bg-clip-text text-transparent max-xl:hidden">PINKY</span>
      </div>

      <div className="px-3 mb-2 max-xl:px-2">
        <div className="h-px bg-gradient-to-r from-transparent via-border-default to-transparent" />
      </div>

      <div className="flex flex-col gap-0.5 px-2 max-xl:px-1">
        {NAV_ITEMS.filter(i => i.section === "primary").map(item => (
          <NavLink key={item.id} item={item} active={pathname.startsWith(item.path)} badge={badges[item.id]} />
        ))}
      </div>

      <div className="flex-1" />

      <div className="px-3 my-2 max-xl:px-2">
        <div className="h-px bg-gradient-to-r from-transparent via-border-default to-transparent" />
      </div>

      <div className="flex flex-col gap-0.5 px-2 pb-4 max-xl:px-1">
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
        "group relative flex items-center gap-2.5 px-3 py-2 rounded-lg text-[13px] no-underline transition-all duration-200",
        active
          ? "text-text-primary font-medium bg-accent/80"
          : "text-text-secondary hover:text-text-primary hover:bg-bg-hover/60"
      )}
    >
      {active && (
        <div className="absolute left-0 top-1/2 -translate-y-1/2 w-[3px] h-4 rounded-r-full bg-accent-brand" />
      )}
      <Icon size={17} strokeWidth={active ? 2.2 : 1.7} className={cn("shrink-0 transition-colors", active ? "text-accent-brand" : "text-text-tertiary group-hover:text-text-secondary")} />
      <span className="flex-1 max-xl:hidden">{item.label}</span>
      {badge != null && badge !== "0" && (
        <span className="text-[10px] font-mono font-semibold tabular bg-accent-brand/15 text-accent-brand px-1.5 py-0.5 rounded-full min-w-5 text-center max-xl:hidden">{badge}</span>
      )}
    </Link>
  );
}
