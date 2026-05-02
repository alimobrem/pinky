export default function TasksPage() {
  return (
    <div>
      <h1 style={{ fontSize: 20, fontWeight: 600, marginBottom: "var(--space-4)" }}>Tasks</h1>

      <div style={{
        display: "flex",
        gap: "var(--space-3)",
        marginBottom: "var(--space-6)",
      }}>
        {[
          { label: "Ready", count: 0, color: "var(--status-ready)" },
          { label: "In Progress", count: 0, color: "var(--status-in-progress)" },
          { label: "Blocked", count: 0, color: "var(--status-blocked)" },
          { label: "Needs Approval", count: 0, color: "var(--status-approval)" },
        ].map(s => (
          <div key={s.label} style={{
            background: "var(--bg-surface)",
            border: "1px solid var(--border-default)",
            borderRadius: 8,
            padding: "var(--space-3) var(--space-4)",
            minWidth: 140,
          }}>
            <div style={{ fontSize: 24, fontWeight: 700 }}>{s.count}</div>
            <div style={{ fontSize: 13, color: s.color }}>{s.label}</div>
          </div>
        ))}
      </div>

      <div style={{
        textAlign: "center",
        padding: "var(--space-8)",
        color: "var(--text-secondary)",
      }}>
        No tasks need human attention right now.
      </div>
    </div>
  );
}
