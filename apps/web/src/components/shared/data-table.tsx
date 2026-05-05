"use client";

import { useState, useCallback, useRef, useEffect, type ReactNode } from "react";
import { cn } from "@/lib/utils";
import { ArrowUp, ArrowDown } from "lucide-react";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useHotkey } from "@/hooks/use-hotkey";

export interface Column<T> {
  id: string;
  header: string;
  cell: (row: T) => ReactNode;
  sortable?: boolean;
  className?: string;
  headerClassName?: string;
}

type SortDir = "asc" | "desc" | null;

interface DataTableProps<T> {
  data: T[];
  columns: Column<T>[];
  keyFn: (row: T) => string;
  onRowClick?: (row: T) => void;
  onRowSelect?: (keys: Set<string>) => void;
  selectedKeys?: Set<string>;
  focusedKey?: string | null;
  onFocusChange?: (key: string | null) => void;
  emptyState?: ReactNode;
  className?: string;
  rowClassName?: (row: T) => string;
  stickyHeader?: boolean;
}

export function DataTable<T>({
  data,
  columns,
  keyFn,
  onRowClick,
  onRowSelect,
  selectedKeys,
  focusedKey,
  onFocusChange,
  emptyState,
  className,
  rowClassName,
  stickyHeader = false,
}: DataTableProps<T>) {
  const [sortCol, setSortCol] = useState<string | null>(null);
  const [sortDir, setSortDir] = useState<SortDir>(null);
  const [internalFocus, setInternalFocus] = useState<number>(-1);
  const tableRef = useRef<HTMLTableElement>(null);

  const focused = focusedKey ?? (internalFocus >= 0 ? keyFn(data[internalFocus]) : null);

  const handleSort = useCallback((colId: string) => {
    setSortCol((prev) => {
      if (prev !== colId) {
        setSortDir("asc");
        return colId;
      }
      setSortDir((d) => {
        if (d === "asc") return "desc";
        if (d === "desc") return null;
        return "asc";
      });
      return colId;
    });
  }, []);

  const moveFocus = useCallback(
    (delta: number) => {
      if (data.length === 0) return;
      setInternalFocus((prev) => {
        const next = Math.max(0, Math.min(data.length - 1, prev + delta));
        onFocusChange?.(keyFn(data[next]));
        return next;
      });
    },
    [data, keyFn, onFocusChange],
  );

  useHotkey("j", () => moveFocus(1));
  useHotkey("k", () => moveFocus(-1));
  useHotkey("enter", () => {
    if (internalFocus >= 0 && onRowClick) {
      onRowClick(data[internalFocus]);
    }
  });
  useHotkey("x", () => {
    if (internalFocus >= 0 && onRowSelect && selectedKeys) {
      const key = keyFn(data[internalFocus]);
      const next = new Set(selectedKeys);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      onRowSelect(next);
    }
  });

  useEffect(() => {
    if (focusedKey && data.length > 0) {
      const idx = data.findIndex((r) => keyFn(r) === focusedKey);
      if (idx >= 0) setInternalFocus(idx);
    }
  }, [focusedKey, data, keyFn]);

  if (data.length === 0 && emptyState) {
    return <>{emptyState}</>;
  }

  return (
    <div className={cn("rounded-lg border border-border-subtle overflow-hidden", className)}>
      <Table ref={tableRef}>
        <TableHeader>
          <TableRow className="border-b border-border-subtle bg-bg-surface hover:bg-bg-surface">
            {columns.map((col) => (
              <TableHead
                key={col.id}
                className={cn(
                  "h-9 text-[11px] font-semibold uppercase tracking-wider text-text-tertiary",
                  stickyHeader && "sticky top-0 z-10 bg-bg-surface",
                  col.sortable && "cursor-pointer select-none hover:text-text-secondary",
                  col.headerClassName,
                )}
                onClick={col.sortable ? () => handleSort(col.id) : undefined}
              >
                <span className="inline-flex items-center gap-1">
                  {col.header}
                  {col.sortable && sortCol === col.id && (
                    sortDir === "asc" ? <ArrowUp size={12} /> : sortDir === "desc" ? <ArrowDown size={12} /> : null
                  )}
                </span>
              </TableHead>
            ))}
          </TableRow>
        </TableHeader>
        <TableBody>
          {data.map((row, i) => {
            const key = keyFn(row);
            const isFocused = key === focused;
            const isSelected = selectedKeys?.has(key);

            return (
              <TableRow
                key={key}
                data-focused={isFocused || undefined}
                data-selected={isSelected || undefined}
                className={cn(
                  "border-b border-border-subtle transition-colors duration-100",
                  isFocused && "bg-bg-hover",
                  isSelected && "bg-brand-purple/5",
                  onRowClick && "cursor-pointer",
                  rowClassName?.(row),
                )}
                onClick={() => onRowClick?.(row)}
                onMouseEnter={() => {
                  setInternalFocus(i);
                  onFocusChange?.(key);
                }}
              >
                {columns.map((col) => (
                  <TableCell key={col.id} className={cn("py-2.5 text-sm", col.className)}>
                    {col.cell(row)}
                  </TableCell>
                ))}
              </TableRow>
            );
          })}
        </TableBody>
      </Table>
    </div>
  );
}
