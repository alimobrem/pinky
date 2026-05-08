import { queryOptions } from "@tanstack/react-query";
import type { HistoryEvent, PaginatedResponse } from "@pinky/contracts";
import { api } from "@/lib/api";
import { QUERY_KEYS } from "@/lib/constants";

export const historyOptions = (filters?: {
  cluster_id?: string;
  event_type?: string;
  cursor?: string;
}) => {
  const params = new URLSearchParams();
  if (filters?.cluster_id) params.set("cluster_id", filters.cluster_id);
  if (filters?.event_type) params.set("event_type", filters.event_type);
  if (filters?.cursor) params.set("cursor", filters.cursor);
  params.set("limit", "50");

  return queryOptions({
    queryKey: QUERY_KEYS.history(filters),
    queryFn: () =>
      api.get<PaginatedResponse<HistoryEvent>>(`/api/v1/history?${params}`),
    staleTime: 15_000,
  });
};
