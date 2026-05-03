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
  icon: ComponentType<{ size?: number; strokeWidth?: number }>;
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
    <nav className="w-[220px] min-h-screen bg-bg-surface border-r border-border-default py-5 flex flex-col max-xl:w-14 max-md:hidden">
      <div className="px-5 pb-8 flex items-center gap-2">
        <Brain size={22} className="text-accent-brain" />
        <span className="text-xl font-extrabold tracking-wider bg-gradient-to-br from-accent-brand to-accent-brain bg-clip-text text-transparent max-xl:hidden">PINKY</span>
      </div>
      <div className="border-b border-border-subtle mx-4 mb-3" />

      {NAV_ITEMS.filter(i => i.section === "primary").map(item => (
        <NavLink key={item.id} item={item} active={pathname.startsWith(item.path)} badge={badges[item.id]} brainDot={item.id === "watch" && brainActive} />
      ))}

      <div className="flex-1" />
      <div className="border-b border-border-subtle mx-4 my-3" />

      {NAV_ITEMS.filter(i => i.section === "secondary").map(item => (
        <NavLink key={item.id} item={item} active={pathname.startsWith(item.path)} />
      ))}
    </nav>
  );
}

function NavLink({ item, active, badge, brainDot }: { item: NavItem; active: boolean; badge?: string; brainDot?: boolean }) {
  const Icon = item.icon;
  return (
    <Link
      href={item.path}
      aria-label={item.label}
      aria-current={active ? "page" : undefined}
      className={cn(
        "flex items-center gap-3 px-5 py-2 text-sm no-underline border-l-3 border-transparent transition-colors",
        active
          ? "text-text-primary font-semibold bg-bg-elevated border-l-accent-brand"
          : "text-text-secondary hover:text-text-primary hover:bg-bg-hover"
      )}
    >
      <Icon size={18} strokeWidth={active ? 2.2 : 1.8} />
      <span className="flex-1 max-xl:hidden">{item.label}</span>
      {badge != null && badge !== "0" && (
        <span className="text-[11px] font-semibold tabular bg-accent-brand text-white px-1.5 py-0.5 rounded-full min-w-5 text-center max-xl:hidden">{badge}</span>
      )}
      {brainDot && <span className="w-2 h-2 rounded-full bg-accent-brain animate-brain-pulse" />}
    </Link>
  );
}
