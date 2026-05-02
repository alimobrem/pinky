export default function SettingsPage() {
  return (
    <div>
      <h1 style={{ fontSize: 20, fontWeight: 600, marginBottom: "var(--space-6)" }}>Settings</h1>

      <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-4)" }}>
        {[
          { title: "Cluster Registry", desc: "Manage registered clusters and observer bindings" },
          { title: "Cluster Bindings", desc: "Your cluster access and binding status" },
          { title: "Service Bindings", desc: "External service connections (Prometheus, Datadog)" },
          { title: "Definitions", desc: "Scanners, tools, skills, pipelines, and policies" },
          { title: "Webhooks", desc: "Outbound notification subscriptions" },
          { title: "Brain Usage", desc: "LLM cost, cache hit rate, and investigation analytics" },
          { title: "Analytics / ROI", desc: "ROI dashboard, scanner quality, eval scores" },
          { title: "API Tokens", desc: "Manage tokens for CLI and CI automation" },
          { title: "Profile", desc: "Your account, linked providers, and active sessions" },
        ].map(s => (
          <div key={s.title} style={{
            background: "var(--bg-surface)",
            border: "1px solid var(--border-default)",
            borderRadius: 8,
            padding: "var(--space-4)",
            cursor: "pointer",
          }}>
            <div style={{ fontWeight: 600, marginBottom: "var(--space-1)" }}>{s.title}</div>
            <div style={{ fontSize: 13, color: "var(--text-secondary)" }}>{s.desc}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
