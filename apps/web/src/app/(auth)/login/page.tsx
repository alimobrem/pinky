"use client";

import { useState } from "react";
import { Brain } from "lucide-react";
import css from "./page.module.css";

export default function LoginPage() {
  const [loading, setLoading] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleLogin = async (provider: string) => {
    setLoading(provider);
    setError(null);
    try {
      const r = await fetch(`/api/v1/auth/login?provider=${provider}`);
      if (!r.ok) {
        setError(`Login failed (${r.status})`);
        setLoading(null);
        return;
      }
      const data = await r.json();
      if (data.authorize_url) {
        window.location.href = data.authorize_url;
      } else {
        setError(data.note || "Provider not configured");
        setLoading(null);
      }
    } catch {
      setError("Network error — is the API running?");
      setLoading(null);
    }
  };

  return (
    <div className={css.container}>
      <div className={css.card}>
        <div className={css.logoRow}>
          <Brain size={32} style={{ color: "var(--accent-brain)" }} />
          <h1 className={css.logoText}>PINKY</h1>
        </div>
        <p className={css.tagline}>Multi-cluster ops.</p>
        <p className={css.taglineBrain}>Powered by The Brain.</p>
        <div className={css.buttons}>
          <button className={css.btnPrimary} onClick={() => handleLogin("openshift")} disabled={loading !== null}>
            {loading === "openshift" ? "Redirecting..." : "Sign in with OpenShift"}
          </button>
          <button className={css.btnSecondary} onClick={() => handleLogin("oidc")} disabled={loading !== null}>
            {loading === "oidc" ? "Redirecting..." : "Sign in with OIDC"}
          </button>
        </div>
        {error && <div className={css.error}>{error}</div>}
        <div className={css.brainStatus}>
          <span className={css.brainDot} />
          Brain status: monitoring clusters
        </div>
      </div>
    </div>
  );
}
