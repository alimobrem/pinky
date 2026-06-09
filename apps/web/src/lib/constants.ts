export const MOTION = {
  open: { duration: 0.25, ease: [0.16, 1, 0.3, 1] as const },
  close: { duration: 0.15, ease: [0.45, 0, 0.55, 1] as const },
  spring: { stiffness: 400, damping: 30 },
  stagger: { staggerChildren: 0.03 },
  item: { duration: 0.2, ease: [0.16, 1, 0.3, 1] as const },
} as const;

export const BREAKPOINTS = {
  sm: 640,
  md: 768,
  lg: 1024,
  xl: 1280,
  "2xl": 1536,
} as const;

export const QUERY_KEYS = {
  tasks: (filters?: unknown) => ["tasks", filters] as const,
  task: (id: string) => ["task", id] as const,
  taskInvestigation: (id: string) => ["task-investigation", id] as const,
  taskTimeline: (id: string) => ["task-timeline", id] as const,
  issues: (filters?: Record<string, unknown>) => ["issues", filters] as const,
  issue: (id: string) => ["issue", id] as const,
  clusters: () => ["clusters"] as const,
  cluster: (id: string) => ["cluster", id] as const,
  clusterNodes: (id: string) => ["cluster-nodes", id] as const,
  clusterNamespaces: (id: string) => ["cluster-namespaces", id] as const,
  clusterEvents: (id: string) => ["cluster-events", id] as const,
  executions: (filters?: Record<string, unknown>) => ["executions", filters] as const,
  execution: (id: string) => ["execution", id] as const,
  alerts: (filters?: Record<string, unknown>) => ["alerts", filters] as const,
  history: (filters?: Record<string, unknown>) => ["history", filters] as const,
  definitions: (kind?: string) => ["definitions", kind] as const,
  webhooks: () => ["webhooks"] as const,
  webhookDeliveries: (subId?: string) => ["webhook-deliveries", subId] as const,
  policyRules: () => ["policy-rules"] as const,
  bindings: () => ["cluster-bindings"] as const,
  apiTokens: () => ["api-tokens"] as const,
  serviceBindings: () => ["service-bindings"] as const,
  session: () => ["session"] as const,
  analyticsRoi: (since?: string) => ["analytics-roi", since] as const,
  analyticsScanners: (since?: string) => ["analytics-scanners", since] as const,
  watchSummary: (since?: string) => ["watch-summary", since] as const,
  observerBinding: (clusterId: string) => ["observer-binding", clusterId] as const,
} as const;

export const SIDEBAR_WIDTH = {
  iconRail: 56,
  detailPanel: 220,
} as const;

export const ENV_STRIPE_HEIGHT = 3;
