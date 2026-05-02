export type ClusterOnboardingState =
  | "pending"
  | "provisioning"
  | "ready"
  | "degraded"
  | "offboarding"
  | "offboarded";

export type ClusterBindingStatus =
  | "missing"
  | "valid"
  | "expiring"
  | "expired"
  | "revoked";

export type ObserverHealthState =
  | "unknown"
  | "healthy"
  | "degraded"
  | "unhealthy";

export interface ClusterRegistryEntry {
  id: string;
  display_name: string;
  api_endpoint: string;
  fleet_identifier: string | null;
  onboarding_state: ClusterOnboardingState;
  offboarding_state: string | null;
  created_at: string;
  updated_at: string;
}

export interface ClusterObserverBinding {
  id: string;
  cluster_id: string;
  auth_method: string;
  health_state: ObserverHealthState;
  last_observation_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface ClusterIdentityBinding {
  id: string;
  principal_id: string;
  cluster_id: string;
  cluster_username: string | null;
  cluster_groups: string[];
  binding_method: string;
  status: ClusterBindingStatus;
  expires_at: string | null;
  created_at: string;
  updated_at: string;
}
