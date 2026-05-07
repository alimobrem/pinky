import type { ReactNode } from "react";

export interface EmptyStateProps {
  message: string;
  children?: ReactNode;
}

export function EmptyState({ message, children }: EmptyStateProps) {
  return (
    <div className="text-center px-4 py-12">
      <p>{message}</p>
      {children}
    </div>
  );
}
