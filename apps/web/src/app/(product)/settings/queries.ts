import { queryOptions } from "@tanstack/react-query";
import type {
  ApiToken,
  ClusterRegistryEntry,
  ClusterObserverBinding,
  Definition,
  WebhookSubscription,
  PolicyRule,
  ClusterIdentityBinding,
  PaginatedResponse,
} from "@pinky/contracts";
import { api, ApiError } from "@/lib/api";
import { QUERY_KEYS } from "@/lib/constants";

export const clustersOptions = () =>
  queryOptions({
    queryKey: QUERY_KEYS.clusters(),
    queryFn: () =>
      api.get<PaginatedResponse<ClusterRegistryEntry>>("/api/v1/clusters"),
    staleTime: 60_000,
  });

export const definitionsOptions = (kind?: string) =>
  queryOptions({
    queryKey: QUERY_KEYS.definitions(kind),
    queryFn: () => {
      const params = kind ? `?kind=${kind}` : "";
      return api.get<PaginatedResponse<Definition>>(`/api/v1/definitions${params}`);
    },
    staleTime: 30_000,
  });

export const webhooksOptions = () =>
  queryOptions({
    queryKey: QUERY_KEYS.webhooks(),
    queryFn: () =>
      api.get<PaginatedResponse<WebhookSubscription>>(
        "/api/v1/webhook-subscriptions",
      ),
    staleTime: 30_000,
  });

export const policyRulesOptions = () =>
  queryOptions({
    queryKey: QUERY_KEYS.policyRules(),
    queryFn: () =>
      api.get<PaginatedResponse<PolicyRule>>("/api/v1/policy-rules"),
    staleTime: 30_000,
  });

export const bindingsOptions = () =>
  queryOptions({
    queryKey: QUERY_KEYS.bindings(),
    queryFn: () =>
      api.get<{ items: ClusterIdentityBinding[] }>("/api/v1/cluster-bindings"),
    staleTime: 30_000,
  });

export const apiTokensOptions = () =>
  queryOptions({
    queryKey: QUERY_KEYS.apiTokens(),
    queryFn: () =>
      api.get<{ items: ApiToken[] }>("/api/v1/api-tokens"),
    staleTime: 30_000,
  });

export const observerBindingOptions = (clusterId: string, enabled: boolean) =>
  queryOptions({
    queryKey: QUERY_KEYS.observerBinding(clusterId),
    queryFn: async () => {
      try {
        return await api.get<ClusterObserverBinding>(
          `/api/v1/clusters/${clusterId}/observer-binding`,
        );
      } catch (err) {
        if (err instanceof ApiError && err.status === 404) return null;
        throw err;
      }
    },
    enabled,
    retry: false,
    staleTime: 30_000,
  });

export const analyticsRoiOptions = (since = "30d") =>
  queryOptions({
    queryKey: QUERY_KEYS.analyticsRoi(since),
    queryFn: () =>
      api.get<{
        period: string;
        metrics: {
          issues_total: number;
          issues_resolved: number;
          tasks_total: number;
          tasks_completed: number;
          executions_total: number;
          task_completion_rate: number;
        };
      }>(`/api/v1/analytics/roi?since=${since}`),
    staleTime: 60_000,
  });

export const analyticsScannersOptions = (since = "30d") =>
  queryOptions({
    queryKey: QUERY_KEYS.analyticsScanners(since),
    queryFn: () =>
      api.get<{
        scanners: {
          scanner: string;
          signal_total: number;
          signal_suppressed: number;
          signal_tasked: number;
          false_positive_rate: number;
          noise_ratio: number;
        }[];
        period: string;
      }>(`/api/v1/analytics/scanners?since=${since}`),
    staleTime: 60_000,
  });

export const analyticsTrendsOptions = (metric: string, period = "7d", bucket = "day") =>
  queryOptions({
    queryKey: ["analytics-trends", metric, period, bucket] as const,
    queryFn: () =>
      api.get<{
        metric: string;
        period: string;
        bucket_size: string;
        buckets: {
          timestamp: string;
          value?: number;
          input_tokens?: number;
          output_tokens?: number;
          call_count?: number;
        }[];
      }>(`/api/v1/analytics/trends?metric=${metric}&period=${period}&bucket=${bucket}`),
    staleTime: 60_000,
  });
