import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

interface PageHeaderProps {
  eyebrow?: string;
  title: string;
  description?: string;
  meta?: ReactNode;
  actions?: ReactNode;
  className?: string;
}

export function PageHeader({
  eyebrow,
  title,
  description,
  meta,
  actions,
  className,
}: PageHeaderProps) {
  return (
    <section
      className={cn(
        "relative overflow-hidden rounded-2xl border border-border-default bg-[linear-gradient(135deg,rgba(15,14,23,0.98),rgba(24,22,36,0.9))] px-5 py-5 shadow-card sm:px-6 sm:py-6",
        className,
      )}
    >
      <div className="pointer-events-none absolute inset-x-0 top-0 h-px bg-[linear-gradient(90deg,rgba(244,114,182,0),rgba(244,114,182,0.5),rgba(167,139,250,0.5),rgba(167,139,250,0))]" />
      <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
        <div className="min-w-0 space-y-3">
          {eyebrow ? (
            <div className="text-[11px] font-semibold uppercase tracking-[0.18em] text-accent-brand/80">
              {eyebrow}
            </div>
          ) : null}
          <div className="space-y-2">
            <h1 className="text-2xl font-semibold tracking-tight text-text-primary sm:text-[28px]">
              {title}
            </h1>
            {description ? (
              <p className="max-w-3xl text-sm leading-relaxed text-text-secondary sm:text-[15px]">
                {description}
              </p>
            ) : null}
          </div>
          {meta ? (
            <div className="flex flex-wrap items-center gap-y-2 text-xs text-text-tertiary [&>*]:inline-flex [&>*]:items-center [&>*+*]:before:mx-3 [&>*+*]:before:text-text-tertiary/45 [&>*+*]:before:content-['•']">
              {meta}
            </div>
          ) : null}
        </div>
        {actions ? (
          <div className="flex shrink-0 flex-wrap items-center gap-2 xl:justify-end">
            {actions}
          </div>
        ) : null}
      </div>
    </section>
  );
}
