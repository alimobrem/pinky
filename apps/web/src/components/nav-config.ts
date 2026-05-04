import {
  AlertTriangle,
  Clock,
  Eye,
  LayoutDashboard,
  Settings,
  CheckSquare,
} from "lucide-react";
import type { ComponentType } from "react";

export interface NavItem {
  id: string;
  label: string;
  path: string;
  icon: ComponentType<{ size?: number; strokeWidth?: number; className?: string }>;
  section: "primary" | "secondary";
}

export const NAV_ITEMS: NavItem[] = [
  { id: "dashboard", label: "Dashboard", path: "/dashboard", icon: LayoutDashboard, section: "primary" },
  { id: "tasks", label: "Tasks", path: "/tasks", icon: CheckSquare, section: "primary" },
  { id: "watch", label: "Watch", path: "/watch", icon: Eye, section: "primary" },
  { id: "history", label: "History", path: "/history", icon: Clock, section: "primary" },
  { id: "alerts", label: "Alerts", path: "/alerts", icon: AlertTriangle, section: "primary" },
  { id: "settings", label: "Settings", path: "/settings", icon: Settings, section: "secondary" },
];
