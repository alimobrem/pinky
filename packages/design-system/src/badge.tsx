import type { ReactNode } from "react";

export interface BadgeProps {
  variant?: "default" | "info" | "success" | "warning" | "danger";
  children: ReactNode;
}

export function Badge({ variant = "default", children }: BadgeProps) {
  return <span data-variant={variant}>{children}</span>;
}
