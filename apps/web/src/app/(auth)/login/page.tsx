export default function LoginPage() {
  return (
    <div style={{
      minHeight: "100vh",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      background: "var(--bg-primary)",
    }}>
      <div style={{
        background: "var(--bg-surface)",
        border: "1px solid var(--border-default)",
        borderRadius: 12,
        padding: "var(--space-8)",
        width: 400,
        textAlign: "center",
      }}>
        <h1 style={{
          fontSize: 32,
          fontWeight: 700,
          color: "var(--accent-brand)",
          marginBottom: "var(--space-2)",
        }}>
          Pinky
        </h1>
        <p style={{
          color: "var(--text-secondary)",
          marginBottom: "var(--space-8)",
          fontSize: 14,
        }}>
          Multi-cluster operations platform
        </p>

        <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-3)" }}>
          <button style={{
            background: "var(--accent-brand)",
            color: "#fff",
            border: "none",
            borderRadius: 6,
            padding: "var(--space-3) var(--space-4)",
            fontSize: 14,
            fontWeight: 600,
            cursor: "pointer",
          }}>
            Sign in with OpenShift
          </button>

          <button style={{
            background: "transparent",
            color: "var(--text-primary)",
            border: "1px solid var(--border-default)",
            borderRadius: 6,
            padding: "var(--space-3) var(--space-4)",
            fontSize: 14,
            fontWeight: 600,
            cursor: "pointer",
          }}>
            Sign in with OIDC
          </button>
        </div>
      </div>
    </div>
  );
}
