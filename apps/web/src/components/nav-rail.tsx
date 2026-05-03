"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { CheckSquare, Eye, Clock, AlertTriangle, Settings, Brain } from "lucide-react";
import type { ComponentType } from "react";
import css from "./nav-rail.module.css";

const API = "";

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
      fetch(`${API}/api/v1/work-items?status=ready`)
        .then(r => r.json())
        .then(d => {
          const count = (d.items || []).length;
          setBadges(prev => ({ ...prev, tasks: d.has_more ? `${count}+` : `${count}` }));
        })
        .catch(() => {});
      fetch(`${API}/api/v1/alerts`)
        .then(r => r.json())
        .then(d => {
          const count = (d.items || []).length;
          setBadges(prev => ({ ...prev, alerts: d.has_more ? `${count}+` : `${count}` }));
        })
        .catch(() => {});
      fetch(`${API}/api/v1/issues?status=open`)
        .then(r => r.json())
        .then(d => setBrainActive((d.items || []).length > 0))
        .catch(() => {});
    };
    fetchBadges();
    const interval = setInterval(fetchBadges, 30000);
    return () => clearInterval(interval);
  }, []);

  return (
    <nav className={css.rail}>
      <div className={css.brand}>
        <Brain size={22} style={{ color: "var(--accent-brain)" }} />
        <span className={css.brandText}>PINKY</span>
      </div>
      <div className={css.divider} />

      {NAV_ITEMS.filter(i => i.section === "primary").map(item => (
        <NavLink key={item.id} item={item} active={pathname.startsWith(item.path)} badge={badges[item.id]} brainDot={item.id === "watch" && brainActive} />
      ))}

      <div className={css.spacer} />
      <div className={css.dividerBottom} />

      {NAV_ITEMS.filter(i => i.section === "secondary").map(item => (
        <NavLink key={item.id} item={item} active={pathname.startsWith(item.path)} />
      ))}
    </nav>
  );
}

function NavLink({ item, active, badge, brainDot }: { item: NavItem; active: boolean; badge?: string; brainDot?: boolean }) {
  const Icon = item.icon;
  return (
    <Link href={item.path} className={active ? css.linkActive : css.link} aria-label={item.label} aria-current={active ? "page" : undefined}>
      <Icon size={18} strokeWidth={active ? 2.2 : 1.8} />
      <span className={css.linkLabel}>{item.label}</span>
      {badge != null && badge !== "0" && <span className={css.badge}>{badge}</span>}
      {brainDot && <span className={css.brainDot} />}
    </Link>
  );
}
