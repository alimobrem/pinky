"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { useQueryClient } from "@tanstack/react-query";
import type { PaginatedResponse } from "@pinky/contracts";
import { useEventBus, type SSEConnectionState } from "@/hooks/use-event-bus";

interface UsePaginatedDataOptions {
  /** Current cursor value — owned by the caller. */
  cursor: string | undefined;
  /** Reset cursor to undefined — called on SSE events. */
  onReset: () => void;
  /** SSE event bus subscription id. Omit to skip SSE reset (e.g. sub-tabs). */
  eventBusId?: string;
  /** Query keys to invalidate on SSE reset. */
  invalidateKeys?: readonly (readonly unknown[])[];
}

interface UsePaginatedDataResult<T> {
  allItems: T[];
  hasMore: boolean;
  totalCount: number | undefined;
  nextCursor: string | undefined;
  /** SSE connection state — only meaningful when eventBusId is set. */
  sseState: SSEConnectionState;
  /** Last SSE update timestamp — only meaningful when eventBusId is set. */
  lastUpdated: Date | null;
}

/**
 * Manages cursor-based page accumulation with dedup and optional SSE reset.
 *
 * The caller owns `cursor` state and the query. This hook owns `allItems`,
 * deduplicates on append, and resets everything when an SSE event fires
 * (if `eventBusId` is provided).
 */
export function usePaginatedData<T extends { id: string }>(
  data: PaginatedResponse<T> | undefined,
  opts: UsePaginatedDataOptions,
): UsePaginatedDataResult<T> {
  const [allItems, setAllItems] = useState<T[]>([]);
  const qc = useQueryClient();

  const invalidateKeysRef = useRef(opts.invalidateKeys);
  invalidateKeysRef.current = opts.invalidateKeys;

  const onResetRef = useRef(opts.onReset);
  onResetRef.current = opts.onReset;

  const reset = useCallback(() => {
    setAllItems([]);
    onResetRef.current();
    for (const key of invalidateKeysRef.current ?? []) {
      qc.invalidateQueries({ queryKey: key });
    }
  }, [qc]);

  // Subscribe to SSE if eventBusId is provided; noop otherwise
  const { state: sseState, lastUpdated } = useEventBus(
    opts.eventBusId ?? "__noop__",
    opts.eventBusId ? reset : () => {},
  );

  useEffect(() => {
    if (!data?.items) return;
    if (!opts.cursor) {
      setAllItems(data.items);
    } else {
      setAllItems((prev) => {
        const existingIds = new Set(prev.map((t) => t.id));
        const newItems = data.items.filter((t) => !existingIds.has(t.id));
        if (newItems.length === 0 && prev.length > 0) return prev;
        return [...prev, ...newItems];
      });
    }
  }, [data, opts.cursor]);

  return {
    allItems,
    hasMore: data?.has_more ?? false,
    totalCount: data?.total_count,
    nextCursor: data?.next_cursor ?? undefined,
    sseState,
    lastUpdated,
  };
}
