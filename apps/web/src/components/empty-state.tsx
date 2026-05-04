import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

interface EmptyStateProps {
  eyebrow?: string;
  title: string;
  description: string;
  icon?: ReactNode;
  action?: ReactNode;
  className?: string;
}

export function EmptyState({
  eyebrow,
  title,
  description,
  icon,
  action,
  className,
}: EmptyStateProps) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center rounded-2xl border border-border-default bg-bg-surface px-6 py-14 text-center shadow-card",
        className,
      )}
    >
      {icon ? (
        <div className="mb-5 flex h-12 w-12 items-center justify-center rounded-2xl border border-border-subtle bg-bg-elevated text-text-tertiary">
          {icon}
        </div>
      ) : null}
      {eyebrow ? (
        <div className="mb-2 text-[11px] font-semibold uppercase tracking-[0.18em] text-accent-brand/75">
          {eyebrow}
        </div>
      ) : null}
      <h2 className="text-base font-semibold text-text-primary sm:text-lg">{title}</h2>
      <p className="mt-2 max-w-md text-sm leading-relaxed text-text-secondary">
        {description}
      </p>
      {action ? <div className="mt-5">{action}</div> : null}
    </div>
  );
}
