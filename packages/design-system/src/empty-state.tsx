import type { ReactNode } from "react";

export interface EmptyStateProps {
  message: string;
  children?: ReactNode;
}

export function EmptyState({ message, children }: EmptyStateProps) {
  return (
    <div style={{ textAlign: "center", padding: "3rem 1rem" }}>
      <p>{message}</p>
      {children}
    </div>
  );
}
