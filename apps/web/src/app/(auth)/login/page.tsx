"use client";

import { Brain } from "lucide-react";

export default function LoginPage() {
  return (
    <div style={{
      minHeight: "100vh",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      background: `
        radial-gradient(ellipse 600px 400px at 50% 40%, rgba(244, 114, 182, 0.06) 0%, transparent 70%),
        radial-gradient(ellipse 400px 300px at 55% 50%, rgba(167, 139, 250, 0.04) 0%, transparent 70%),
        var(--bg-primary)
      `,
    }}>
      <div style={{
        background: "var(--bg-surface)",
        border: "1px solid var(--border-default)",
        borderRadius: "var(--radius-xl)",
        padding: "var(--space-10)",
        width: 420,
        textAlign: "center",
      }}>
        <div style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          gap: "var(--space-3)",
          marginBottom: "var(--space-3)",
        }}>
          <Brain size={32} style={{ color: "var(--accent-brain)" }} />
          <h1 style={{
            fontSize: 36,
            fontWeight: 800,
            letterSpacing: "0.08em",
            background: "var(--gradient-brand)",
            WebkitBackgroundClip: "text",
            WebkitTextFillColor: "transparent",
            backgroundClip: "text",
          }}>
            PINKY
          </h1>
        </div>

        <p style={{ color: "var(--text-secondary)", fontSize: 14, marginBottom: "var(--space-1)" }}>
          Multi-cluster ops.
        </p>
        <p style={{ color: "var(--accent-brain)", fontSize: 13, marginBottom: "var(--space-10)" }}>
          Powered by The Brain.
        </p>

        <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-3)" }}>
          <button style={{
            width: "100%",
            padding: "12px 16px",
            background: "var(--accent-brand)",
            color: "#fff",
            border: "none",
            borderRadius: "var(--radius-md)",
            fontSize: 14,
            fontWeight: 600,
            cursor: "pointer",
            transition: "background var(--transition-fast)",
          }}>
            Sign in with OpenShift
          </button>

          <button style={{
            width: "100%",
            padding: "12px 16px",
            background: "transparent",
            color: "var(--text-primary)",
            border: "1px solid var(--border-default)",
            borderRadius: "var(--radius-md)",
            fontSize: 14,
            fontWeight: 600,
            cursor: "pointer",
            transition: "background var(--transition-fast), border-color var(--transition-fast)",
          }}>
            Sign in with OIDC
          </button>
        </div>

        <div style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          gap: "var(--space-2)",
          marginTop: "var(--space-8)",
          fontSize: 12,
          color: "var(--text-tertiary)",
        }}>
          <span style={{
            width: 6,
            height: 6,
            borderRadius: "50%",
            background: "var(--accent-brain)",
            display: "inline-block",
            animation: "brain-pulse 2s ease-in-out infinite",
          }} />
          Brain status: monitoring clusters
        </div>
      </div>
    </div>
  );
}
