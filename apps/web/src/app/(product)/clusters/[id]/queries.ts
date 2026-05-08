import { queryOptions } from "@tanstack/react-query";
import type {
  ClusterDetail,
  ClusterNode,
  ClusterNamespace,
  K8sEvent,
  Issue,
  PaginatedResponse,
} from "@pinky/contracts";
import { api } from "@/lib/api";
import { QUERY_KEYS } from "@/lib/constants";

export const clusterDetailOptions = (id: string) =>
  queryOptions({
    queryKey: QUERY_KEYS.cluster(id),
    queryFn: () => api.get<ClusterDetail>(`/api/v1/clusters/${id}`),
    staleTime: 30_000,
  });

export const clusterNodesOptions = (id: string) =>
  queryOptions({
    queryKey: QUERY_KEYS.clusterNodes(id),
    queryFn: () =>
      api.get<{ items: ClusterNode[] }>(`/api/v1/clusters/${id}/nodes`),
    staleTime: 30_000,
  });

export const clusterNamespacesOptions = (id: string) =>
  queryOptions({
    queryKey: QUERY_KEYS.clusterNamespaces(id),
    queryFn: () =>
      api.get<{ items: ClusterNamespace[] }>(
        `/api/v1/clusters/${id}/namespaces`,
      ),
    staleTime: 30_000,
  });

export const clusterEventsOptions = (id: string) =>
  queryOptions({
    queryKey: QUERY_KEYS.clusterEvents(id),
    queryFn: () =>
      api.get<{ items: K8sEvent[] }>(`/api/v1/clusters/${id}/events`),
    staleTime: 15_000,
  });

export const clusterIssuesOptions = (clusterId: string) =>
  queryOptions({
    queryKey: QUERY_KEYS.issues({ cluster_id: clusterId }),
    queryFn: () =>
      api.get<PaginatedResponse<Issue>>(
        `/api/v1/issues?cluster_id=${clusterId}&limit=100`,
      ),
    staleTime: 15_000,
  });
