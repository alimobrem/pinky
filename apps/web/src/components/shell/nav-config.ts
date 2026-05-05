import type { ComponentType } from "react";
import {
  LayoutDashboard,
  ListTodo,
  Eye,
  Clock,
  Bell,
  Settings,
} from "lucide-react";

export interface NavItem {
  id: string;
  label: string;
  path: string;
  icon: ComponentType<{ size?: number; strokeWidth?: number; className?: string }>;
  section: "primary" | "secondary";
  shortcut?: string;
}

export const NAV_ITEMS: NavItem[] = [
  {
    id: "dashboard",
    label: "Dashboard",
    path: "/dashboard",
    icon: LayoutDashboard,
    section: "primary",
    shortcut: "g+d",
  },
  {
    id: "tasks",
    label: "Tasks",
    path: "/tasks",
    icon: ListTodo,
    section: "primary",
    shortcut: "g+t",
  },
  {
    id: "watch",
    label: "Watch",
    path: "/watch",
    icon: Eye,
    section: "primary",
    shortcut: "g+w",
  },
  {
    id: "history",
    label: "History",
    path: "/history",
    icon: Clock,
    section: "primary",
    shortcut: "g+h",
  },
  {
    id: "alerts",
    label: "Alerts",
    path: "/alerts",
    icon: Bell,
    section: "primary",
    shortcut: "g+a",
  },
  {
    id: "settings",
    label: "Settings",
    path: "/settings",
    icon: Settings,
    section: "secondary",
    shortcut: "g+s",
  },
];
