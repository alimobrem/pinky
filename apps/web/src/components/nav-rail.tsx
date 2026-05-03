"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { CheckSquare, Eye, Clock, AlertTriangle, Settings, Brain } from "lucide-react";
import type { ComponentType } from "react";

interface NavItem {
  id: string;
  label: string;
  path: string;
  icon: ComponentType<{ size?: number; strokeWidth?: number }>;
  section: "primary" | "secondary" | "plugin";
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

  return (
    <nav style={{
      width: 220,
      minHeight: "100vh",
      background: "var(--bg-surface)",
      borderRight: "1px solid var(--border-default)",
      padding: "var(--space-5) 0",
      display: "flex",
      flexDirection: "column",
    }}>
      <div style={{
        padding: "0 var(--space-5) var(--space-8)",
        display: "flex",
        alignItems: "center",
        gap: "var(--space-2)",
      }}>
        <Brain size={22} style={{ color: "var(--accent-brain)" }} />
        <span style={{
          fontSize: 20,
          fontWeight: 800,
          letterSpacing: "0.04em",
          background: "var(--gradient-brand)",
          WebkitBackgroundClip: "text",
          WebkitTextFillColor: "transparent",
          backgroundClip: "text",
        }}>
          PINKY
        </span>
      </div>

      <div style={{ borderBottom: "1px solid var(--border-subtle)", margin: "0 var(--space-4) var(--space-3)" }} />

      {NAV_ITEMS.filter(i => i.section === "primary").map(item => (
        <NavLink key={item.id} item={item} active={pathname.startsWith(item.path)} />
      ))}

      <div style={{ flex: 1 }} />

      <div style={{ borderBottom: "1px solid var(--border-subtle)", margin: "var(--space-3) var(--space-4)" }} />

      {NAV_ITEMS.filter(i => i.section === "secondary").map(item => (
        <NavLink key={item.id} item={item} active={pathname.startsWith(item.path)} />
      ))}
    </nav>
  );
}

function NavLink({ item, active }: { item: NavItem; active: boolean }) {
  const Icon = item.icon;
  return (
    <Link
      href={item.path}
      style={{
        display: "flex",
        alignItems: "center",
        gap: "var(--space-3)",
        padding: "var(--space-2) var(--space-5)",
        color: active ? "var(--text-primary)" : "var(--text-secondary)",
        background: active ? "var(--bg-elevated)" : "transparent",
        borderLeft: active ? "3px solid var(--accent-brand)" : "3px solid transparent",
        fontSize: 14,
        fontWeight: active ? 600 : 400,
        textDecoration: "none",
        transition: "color var(--transition-fast), background var(--transition-fast)",
      }}
    >
      <Icon size={18} strokeWidth={active ? 2.2 : 1.8} />
      {item.label}
    </Link>
  );
}
