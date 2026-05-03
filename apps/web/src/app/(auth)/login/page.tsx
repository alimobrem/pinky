"use client";

import { useState } from "react";
import { Brain } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";

export default function LoginPage() {
  const [loading, setLoading] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleLogin = async (provider: string) => {
    setLoading(provider);
    setError(null);
    try {
      const r = await fetch(`/api/v1/auth/login?provider=${provider}`);
      if (!r.ok) { setError(`Login failed (${r.status})`); setLoading(null); return; }
      const data = await r.json();
      if (data.authorize_url) window.location.href = data.authorize_url;
      else { setError(data.note || "Provider not configured"); setLoading(null); }
    } catch { setError("Network error — is the API running?"); setLoading(null); }
  };

  return (
    <div className="flex items-center justify-center min-h-screen bg-bg-primary">
      <Card className="w-[420px] p-8 text-center bg-bg-surface border-border-default">
        <div className="flex items-center justify-center gap-3 mb-4">
          <Brain size={32} className="text-accent-brain" />
          <h1 className="text-3xl font-extrabold tracking-wider bg-[var(--gradient-brand)] bg-clip-text text-transparent">PINKY</h1>
        </div>
        <p className="text-text-secondary text-sm mb-1">Multi-cluster ops.</p>
        <p className="text-accent-brain text-sm mb-6">Powered by The Brain.</p>
        <div className="flex flex-col gap-3">
          <Button className="w-full" onClick={() => handleLogin("openshift")} disabled={loading !== null}>
            {loading === "openshift" ? "Redirecting..." : "Sign in with OpenShift"}
          </Button>
          <Button variant="outline" className="w-full" onClick={() => handleLogin("oidc")} disabled={loading !== null}>
            {loading === "oidc" ? "Redirecting..." : "Sign in with OIDC"}
          </Button>
        </div>
        {error && <div className="mt-4 p-3 rounded-md bg-status-blocked/10 border border-status-blocked/30 text-status-blocked text-sm">{error}</div>}
        <div className="mt-6 flex items-center justify-center gap-2 text-xs text-text-tertiary">
          <span className="w-2 h-2 rounded-full bg-status-done" />
          Brain status: monitoring clusters
        </div>
      </Card>
    </div>
  );
}
