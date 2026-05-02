export default function WatchPage() {
  return (
    <div>
      <h1 style={{ fontSize: 20, fontWeight: 600, marginBottom: "var(--space-4)" }}>Watch</h1>

      <div style={{
        display: "flex",
        alignItems: "center",
        gap: "var(--space-2)",
        marginBottom: "var(--space-6)",
        fontSize: 13,
        color: "var(--text-secondary)",
      }}>
        <span style={{
          width: 8,
          height: 8,
          borderRadius: "50%",
          background: "var(--status-done)",
          display: "inline-block",
        }} />
        Live
      </div>

      <div style={{
        textAlign: "center",
        padding: "var(--space-8)",
        color: "var(--text-secondary)",
      }}>
        The Brain is not actively escalating anything right now.
      </div>
    </div>
  );
}
