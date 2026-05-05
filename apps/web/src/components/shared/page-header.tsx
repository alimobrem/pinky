import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

interface PageHeaderProps {
  title: string;
  description?: string;
  meta?: ReactNode;
  actions?: ReactNode;
  className?: string;
}

export function PageHeader({
  title,
  description,
  meta,
  actions,
  className,
}: PageHeaderProps) {
  return (
    <header className={cn("mb-6 space-y-1", className)}>
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0 space-y-1">
          <h1 className="text-xl font-bold tracking-tight text-text-primary sm:text-2xl">
            {title}
          </h1>
          {description && (
            <p className="max-w-2xl text-[13px] leading-relaxed text-text-secondary">
              {description}
            </p>
          )}
        </div>
        {actions && (
          <div className="flex shrink-0 items-center gap-2">{actions}</div>
        )}
      </div>
      {meta && (
        <div className="flex items-center gap-3 text-[11px] text-text-tertiary">
          {meta}
        </div>
      )}
    </header>
  );
}
