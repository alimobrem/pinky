import { queryOptions } from "@tanstack/react-query";
import type { Execution, TimelineEvent } from "@pinky/contracts";
import { api } from "@/lib/api";
import { QUERY_KEYS } from "@/lib/constants";

export const executionOptions = (id: string) =>
  queryOptions({
    queryKey: QUERY_KEYS.execution(id),
    queryFn: () => api.get<Execution>(`/api/v1/executions/${id}`),
    staleTime: 3_000,
    refetchInterval: 5_000,
  });

export const executionEventsOptions = (workItemId: string) =>
  queryOptions({
    queryKey: QUERY_KEYS.taskTimeline(workItemId),
    queryFn: () =>
      api.get<{ items: TimelineEvent[] }>(
        `/api/v1/work-items/${workItemId}/events`,
      ),
    staleTime: 3_000,
    refetchInterval: 5_000,
  });
