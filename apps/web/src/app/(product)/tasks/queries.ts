import { queryOptions } from "@tanstack/react-query";
import type {
  WorkItem,
  ClusterRegistryEntry,
  PaginatedResponse,
} from "@pinky/contracts";
import { api } from "@/lib/api";
import { QUERY_KEYS } from "@/lib/constants";

export interface TaskFilters {
  status?: string;
  cluster_id?: string;
  priority?: string;
  search?: string;
  owner?: string;
}

export const tasksOptions = (filters?: TaskFilters & { cursor?: string }) => {
  const params = new URLSearchParams();
  if (filters?.status && filters.status !== "all") params.set("status", filters.status);
  if (filters?.cluster_id) params.set("cluster_id", filters.cluster_id);
  if (filters?.priority) params.set("priority", filters.priority);
  if (filters?.owner) params.set("owner", filters.owner);
  if (filters?.cursor) params.set("cursor", filters.cursor);
  params.set("limit", "50");
  const qs = params.toString();

  return queryOptions({
    queryKey: QUERY_KEYS.tasks(filters),
    queryFn: () =>
      api.get<PaginatedResponse<WorkItem>>(`/api/v1/work-items?${qs}`),
    staleTime: 30_000,
  });
};

export const clustersOptions = () =>
  queryOptions({
    queryKey: QUERY_KEYS.clusters(),
    queryFn: () =>
      api.get<PaginatedResponse<ClusterRegistryEntry>>("/api/v1/clusters"),
    staleTime: 60_000,
  });
