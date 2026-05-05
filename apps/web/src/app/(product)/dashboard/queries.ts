import { queryOptions } from "@tanstack/react-query";
import type {
  WorkItem,
  Issue,
  HistoryEvent,
  ClusterRegistryEntry,
  PaginatedResponse,
} from "@pinky/contracts";
import { api } from "@/lib/api";
import { QUERY_KEYS } from "@/lib/constants";

export const dashboardTasksOptions = () =>
  queryOptions({
    queryKey: [...QUERY_KEYS.tasks(), "dashboard"],
    queryFn: () =>
      api.get<PaginatedResponse<WorkItem>>("/api/v1/work-items?limit=50"),
    staleTime: 30_000,
  });

export const dashboardIssuesOptions = () =>
  queryOptions({
    queryKey: [...QUERY_KEYS.issues(), "dashboard"],
    queryFn: () =>
      api.get<PaginatedResponse<Issue>>("/api/v1/issues?status=open&limit=10"),
    staleTime: 30_000,
  });

export const dashboardHistoryOptions = () =>
  queryOptions({
    queryKey: [...QUERY_KEYS.history(), "dashboard"],
    queryFn: () =>
      api.get<PaginatedResponse<HistoryEvent>>("/api/v1/history?limit=8"),
    staleTime: 30_000,
  });

export const clustersOptions = () =>
  queryOptions({
    queryKey: QUERY_KEYS.clusters(),
    queryFn: () =>
      api.get<PaginatedResponse<ClusterRegistryEntry>>("/api/v1/clusters"),
    staleTime: 60_000,
  });
