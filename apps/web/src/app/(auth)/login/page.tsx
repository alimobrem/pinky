"use client";

import { useState } from "react";
import { Brain } from "lucide-react";
import { Button } from "@/components/ui/button";

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
    <div className="relative flex items-center justify-center min-h-screen bg-background overflow-hidden">
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[700px] h-[700px] rounded-full bg-accent-brain/[0.08] blur-[150px] pointer-events-none" />
      <div className="absolute top-[40%] left-[35%] w-[500px] h-[500px] rounded-full bg-accent-brand/[0.06] blur-[120px] pointer-events-none" />

      <div className="relative w-[400px] animate-fade-in">
        <div className="bg-card border border-border rounded-2xl shadow-elevated overflow-hidden">
          {/* Header section */}
          <div className="flex flex-col items-center pt-12 pb-8 px-8">
            <div className="relative mb-6">
              <div className="absolute -inset-8 bg-accent-brain/40 blur-3xl rounded-full" />
              <div className="absolute -inset-4 bg-accent-brain/30 blur-xl rounded-full" />
              <Brain size={40} className="relative text-accent-brain drop-shadow-[0_0_20px_rgba(167,139,250,0.8)]" />
            </div>
            <h1 className="text-3xl font-bold tracking-[0.12em] bg-gradient-to-br from-accent-brand via-accent-brand to-accent-brain bg-clip-text text-transparent">
              PINKY
            </h1>
            <p className="text-text-tertiary text-sm mt-3">Multi-cluster ops.</p>
            <p className="text-accent-brain text-sm mt-1">Powered by The Brain.</p>
          </div>

          {/* Button section */}
          <div className="flex flex-col gap-3 px-8 pb-8">
            <Button className="w-full h-11 text-sm font-semibold" onClick={() => handleLogin("openshift")} disabled={loading !== null}>
              {loading === "openshift" ? "Redirecting..." : "Sign in with OpenShift"}
            </Button>
            <Button variant="outline" className="w-full h-11 text-sm" onClick={() => handleLogin("oidc")} disabled={loading !== null}>
              {loading === "oidc" ? "Redirecting..." : "Sign in with OIDC"}
            </Button>
          </div>

          {error && (
            <div className="mx-8 mb-6 p-3 rounded-lg bg-destructive/10 border border-destructive/20 text-destructive text-xs font-medium">
              {error}
            </div>
          )}
        </div>

        <div className="flex items-center justify-center gap-2 mt-6 text-xs text-text-tertiary">
          <span className="w-1.5 h-1.5 rounded-full bg-status-done animate-brain-pulse" />
          <span className="font-mono">brain online — monitoring clusters</span>
        </div>
      </div>
    </div>
  );
}
