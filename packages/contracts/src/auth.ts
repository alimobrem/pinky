export type AuthProvider = "openshift" | "oidc";

export type LoginState =
  | "unauthenticated"
  | "authenticating"
  | "login_failed"
  | "signed_in";

export interface Session {
  id: string;
  principal_id: string;
  idle_expires_at: string;
  absolute_expires_at: string;
  created_at: string;
}

export interface AuthProviderConfig {
  provider: AuthProvider;
  display_name: string;
  enabled: boolean;
}
