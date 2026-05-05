export interface Definition {
  id: string;
  kind: string;
  name: string;
  version: string;
  enabled: boolean;
  frontmatter: Record<string, unknown>;
  body: string;
  source: "filesystem" | "database";
  created_at: string;
  updated_at: string;
}

export interface ApiToken {
  id: string;
  name: string;
  scopes: string[];
  last_used_at: string | null;
  expires_at: string | null;
  created_at: string;
}

export interface ApiTokenCreateResponse extends ApiToken {
  token: string;
}

export interface WebhookSubscription {
  id: string;
  name: string;
  url: string;
  event_patterns: string[];
  formatter: string;
  enabled: boolean;
  created_at: string;
  updated_at: string;
}

export interface PolicyRule {
  id: string;
  name: string;
  description: string | null;
  priority: number;
  conditions: Record<string, unknown>;
  action: Record<string, unknown>;
  enabled: boolean;
  created_at: string;
  updated_at: string;
}
