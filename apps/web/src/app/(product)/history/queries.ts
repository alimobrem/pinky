import { infiniteQueryOptions } from "@tanstack/react-query";
import type { HistoryEvent, PaginatedResponse } from "@pinky/contracts";
import { api } from "@/lib/api";
import { QUERY_KEYS } from "@/lib/constants";

export const historyOptions = (filters?: { cluster_id?: string; event_type?: string }) => {
  return infiniteQueryOptions({
    queryKey: QUERY_KEYS.history(filters),
    queryFn: ({ pageParam }) => {
      const params = new URLSearchParams();
      if (filters?.cluster_id) params.set("cluster_id", filters.cluster_id);
      if (filters?.event_type) params.set("event_type", filters.event_type);
      if (pageParam) params.set("cursor", pageParam);
      params.set("limit", "50");
      return api.get<PaginatedResponse<HistoryEvent>>(`/api/v1/history?${params}`);
    },
    getNextPageParam: (lastPage) => lastPage.next_cursor ?? undefined,
    initialPageParam: undefined as string | undefined,
    staleTime: 15_000,
  });
};
