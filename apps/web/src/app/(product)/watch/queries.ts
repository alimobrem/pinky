import { queryOptions } from "@tanstack/react-query";
import type { Issue, Observation, PaginatedResponse } from "@pinky/contracts";
import { api } from "@/lib/api";
import { QUERY_KEYS } from "@/lib/constants";

export const issuesOptions = (filters?: { cluster_id?: string; severity?: string; status?: string }) => {
  const params = new URLSearchParams();
  if (filters?.cluster_id) params.set("cluster_id", filters.cluster_id);
  if (filters?.severity) params.set("severity", filters.severity);
  if (filters?.status && filters.status !== "all") params.set("status", filters.status);
  params.set("limit", "500");

  return queryOptions({
    queryKey: QUERY_KEYS.issues(filters),
    queryFn: () => api.get<PaginatedResponse<Issue>>(`/api/v1/issues?${params}`),
    staleTime: 15_000,
  });
};

export const alertsOptions = (filters?: { cluster_id?: string; severity?: string }) => {
  const params = new URLSearchParams();
  if (filters?.cluster_id) params.set("cluster_id", filters.cluster_id);
  if (filters?.severity) params.set("severity", filters.severity);
  params.set("limit", "100");

  return queryOptions({
    queryKey: QUERY_KEYS.alerts(filters),
    queryFn: () => api.get<PaginatedResponse<Observation>>(`/api/v1/alerts?${params}`),
    staleTime: 15_000,
  });
};
