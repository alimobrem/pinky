"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ComponentType, ReactNode } from "react";

interface NavItem {
  id: string;
  label: string;
  path: string;
  section: "primary" | "secondary" | "plugin";
}

const NAV_ITEMS: NavItem[] = [
  { id: "tasks", label: "Tasks", path: "/tasks", section: "primary" },
  { id: "watch", label: "Watch", path: "/watch", section: "primary" },
  { id: "history", label: "History", path: "/history", section: "primary" },
  { id: "alerts", label: "Alerts", path: "/alerts", section: "primary" },
  { id: "settings", label: "Settings", path: "/settings", section: "secondary" },
];

export function NavRail() {
  const pathname = usePathname();

  return (
    <nav style={{
      width: 200,
      minHeight: "100vh",
      background: "var(--bg-surface)",
      borderRight: "1px solid var(--border-default)",
      padding: "var(--space-4) 0",
      display: "flex",
      flexDirection: "column",
      gap: "var(--space-1)",
    }}>
      <div style={{
        padding: "0 var(--space-4) var(--space-6)",
        fontSize: 20,
        fontWeight: 700,
        color: "var(--accent-brand)",
      }}>
        Pinky
      </div>

      {NAV_ITEMS.filter(i => i.section === "primary").map(item => (
        <NavLink key={item.id} item={item} active={pathname.startsWith(item.path)} />
      ))}

      <div style={{ flex: 1 }} />

      {NAV_ITEMS.filter(i => i.section === "secondary").map(item => (
        <NavLink key={item.id} item={item} active={pathname.startsWith(item.path)} />
      ))}
    </nav>
  );
}

function NavLink({ item, active }: { item: NavItem; active: boolean }) {
  return (
    <Link
      href={item.path}
      style={{
        display: "block",
        padding: "var(--space-2) var(--space-4)",
        color: active ? "var(--text-primary)" : "var(--text-secondary)",
        background: active ? "var(--bg-elevated)" : "transparent",
        borderLeft: active ? "3px solid var(--accent-brand)" : "3px solid transparent",
        fontSize: 14,
        fontWeight: active ? 600 : 400,
        textDecoration: "none",
      }}
    >
      {item.label}
    </Link>
  );
}
