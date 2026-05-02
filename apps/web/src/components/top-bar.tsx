"use client";

export function TopBar() {
  return (
    <header style={{
      height: 48,
      background: "var(--bg-surface)",
      borderBottom: "1px solid var(--border-default)",
      display: "flex",
      alignItems: "center",
      justifyContent: "space-between",
      padding: "0 var(--space-4)",
    }}>
      <div style={{ display: "flex", alignItems: "center", gap: "var(--space-4)" }}>
        <select
          style={{
            background: "var(--bg-elevated)",
            color: "var(--text-primary)",
            border: "1px solid var(--border-default)",
            borderRadius: 4,
            padding: "var(--space-1) var(--space-2)",
            fontSize: 13,
          }}
          defaultValue="all"
        >
          <option value="all">All Clusters</option>
        </select>

        <kbd style={{
          background: "var(--bg-elevated)",
          border: "1px solid var(--border-default)",
          borderRadius: 4,
          padding: "2px 8px",
          fontSize: 12,
          color: "var(--text-secondary)",
          cursor: "pointer",
        }}>
          ⌘K
        </kbd>
      </div>

      <div style={{
        display: "flex",
        alignItems: "center",
        gap: "var(--space-3)",
        color: "var(--text-secondary)",
        fontSize: 13,
      }}>
        <span style={{
          width: 8,
          height: 8,
          borderRadius: "50%",
          background: "var(--status-done)",
          display: "inline-block",
        }} />
        <span>Session active</span>
      </div>
    </header>
  );
}
