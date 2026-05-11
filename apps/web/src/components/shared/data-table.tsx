"use client";

import { useState, useCallback, useRef, useEffect, useMemo, type ReactNode } from "react";
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
  sortValue?: (row: T) => string | number;
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

  const sortedData = useMemo(() => {
    if (!sortCol || !sortDir) return data;
    const col = columns.find((c) => c.id === sortCol);
    if (!col?.sortable) return data;
    const getValue = col.sortValue ?? ((row: T) => {
      const v = (row as Record<string, unknown>)[col.id];
      return typeof v === "string" || typeof v === "number" ? v : String(v ?? "");
    });
    const sorted = [...data].sort((a, b) => {
      const va = getValue(a);
      const vb = getValue(b);
      if (typeof va === "number" && typeof vb === "number") return va - vb;
      return String(va).localeCompare(String(vb));
    });
    return sortDir === "desc" ? sorted.reverse() : sorted;
  }, [data, sortCol, sortDir, columns]);

  const focused = focusedKey ?? (internalFocus >= 0 ? keyFn(sortedData[internalFocus]) : null);

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
        onFocusChange?.(keyFn(sortedData[next]));
        return next;
      });
    },
    [data, sortedData, keyFn, onFocusChange],
  );

  useHotkey("j", () => moveFocus(1));
  useHotkey("k", () => moveFocus(-1));
  useHotkey("enter", () => {
    if (internalFocus >= 0 && onRowClick) {
      onRowClick(sortedData[internalFocus]);
    }
  });
  useHotkey("x", () => {
    if (internalFocus >= 0 && onRowSelect && selectedKeys) {
      const key = keyFn(sortedData[internalFocus]);
      const next = new Set(selectedKeys);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      onRowSelect(next);
    }
  });

  useEffect(() => {
    if (focusedKey && sortedData.length > 0) {
      const idx = sortedData.findIndex((r) => keyFn(r) === focusedKey);
      if (idx >= 0) setInternalFocus(idx);
    }
  }, [focusedKey, sortedData, keyFn]);

  if (sortedData.length === 0 && emptyState) {
    return <>{emptyState}</>;
  }

  return (
    <div className={cn("rounded-lg border border-border-default overflow-hidden", className)}>
      <Table ref={tableRef}>
        <TableHeader>
          <TableRow className="border-b border-border-default bg-bg-surface hover:bg-bg-surface">
            {columns.map((col) => (
              <TableHead
                key={col.id}
                className={cn(
                  "h-9 text-caption font-semibold uppercase tracking-wider text-text-tertiary",
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
          {sortedData.map((row, i) => {
            const key = keyFn(row);
            const isFocused = key === focused;
            const isSelected = selectedKeys?.has(key);

            return (
              <TableRow
                key={key}
                data-focused={isFocused || undefined}
                data-selected={isSelected || undefined}
                className={cn(
                  "border-b border-border-default/50 transition-colors duration-100",
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
