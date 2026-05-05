"use client";

import type { ReactNode } from "react";
import { cn } from "@/lib/utils";
import { Search } from "lucide-react";
import { Input } from "@/components/ui/input";

interface SearchFilterBarProps {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  filters?: ReactNode;
  actions?: ReactNode;
  className?: string;
}

export function SearchFilterBar({
  value,
  onChange,
  placeholder = "Search...",
  filters,
  actions,
  className,
}: SearchFilterBarProps) {
  return (
    <div
      className={cn(
        "flex flex-wrap items-center gap-2 rounded-lg border border-border-subtle bg-bg-surface px-3 py-2",
        className,
      )}
    >
      <div className="relative flex-1">
        <Search
          size={14}
          className="absolute left-0 top-1/2 -translate-y-1/2 text-text-tertiary"
        />
        <Input
          type="text"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder}
          className="h-7 border-0 bg-transparent pl-5 text-sm shadow-none placeholder:text-text-tertiary focus-visible:ring-0"
        />
      </div>
      {filters && (
        <div className="flex items-center gap-1.5 border-l border-border-subtle pl-2">
          {filters}
        </div>
      )}
      {actions && (
        <div className="flex items-center gap-1.5 border-l border-border-subtle pl-2">
          {actions}
        </div>
      )}
    </div>
  );
}
