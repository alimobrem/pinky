import { queryOptions } from "@tanstack/react-query";
import type {
  WorkItem,
  Investigation,
  TimelineEvent,
  Execution,
  PaginatedResponse,
} from "@pinky/contracts";
import { api } from "@/lib/api";
import { QUERY_KEYS } from "@/lib/constants";

export const taskOptions = (id: string) =>
  queryOptions({
    queryKey: QUERY_KEYS.task(id),
    queryFn: () => api.get<WorkItem>(`/api/v1/work-items/${id}`),
    staleTime: 10_000,
  });

export const investigationOptions = (id: string) =>
  queryOptions({
    queryKey: QUERY_KEYS.taskInvestigation(id),
    queryFn: () =>
      api.get<Investigation>(`/api/v1/work-items/${id}/investigation`),
    staleTime: 30_000,
  });

export const timelineOptions = (id: string) =>
  queryOptions({
    queryKey: QUERY_KEYS.taskTimeline(id),
    queryFn: () =>
      api.get<{ items: TimelineEvent[] }>(`/api/v1/work-items/${id}/events`),
    staleTime: 10_000,
  });

export const executionsOptions = (workItemId: string) =>
  queryOptions({
    queryKey: [...QUERY_KEYS.executions(), workItemId],
    queryFn: () =>
      api.get<PaginatedResponse<Execution>>(
        `/api/v1/executions?work_item_id=${workItemId}`,
      ),
    staleTime: 10_000,
  });
