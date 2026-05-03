"use client";

import { Brain } from "lucide-react";
import css from "./page.module.css";

export default function LoginPage() {
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
          <button className={css.btnPrimary}>Sign in with OpenShift</button>
          <button className={css.btnSecondary}>Sign in with OIDC</button>
        </div>
        <div className={css.brainStatus}>
          <span className={css.brainDot} />
          Brain status: monitoring clusters
        </div>
      </div>
    </div>
  );
}
