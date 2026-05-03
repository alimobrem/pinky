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
      {/* Ambient glow */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] rounded-full bg-accent-brain/[0.03] blur-[120px] pointer-events-none" />
      <div className="absolute top-1/3 left-1/3 w-[400px] h-[400px] rounded-full bg-accent-brand/[0.03] blur-[100px] pointer-events-none" />

      <div className="relative w-[400px] animate-fade-in">
        {/* Card */}
        <div className="bg-card border border-border rounded-2xl p-8 shadow-elevated">
          {/* Logo */}
          <div className="flex flex-col items-center mb-8">
            <div className="relative mb-4">
              <div className="absolute inset-0 bg-accent-brain/20 blur-xl rounded-full" />
              <Brain size={40} className="relative text-accent-brain" />
            </div>
            <h1 className="text-3xl font-bold tracking-[0.1em] bg-gradient-to-br from-accent-brand via-accent-brand to-accent-brain bg-clip-text text-transparent">
              PINKY
            </h1>
            <p className="text-text-tertiary text-sm mt-2">Multi-cluster operations</p>
          </div>

          {/* Buttons */}
          <div className="flex flex-col gap-3">
            <Button className="w-full h-11 text-sm font-semibold" onClick={() => handleLogin("openshift")} disabled={loading !== null}>
              {loading === "openshift" ? "Redirecting..." : "Sign in with OpenShift"}
            </Button>
            <Button variant="outline" className="w-full h-11 text-sm" onClick={() => handleLogin("oidc")} disabled={loading !== null}>
              {loading === "oidc" ? "Redirecting..." : "Sign in with OIDC"}
            </Button>
          </div>

          {error && (
            <div className="mt-4 p-3 rounded-lg bg-destructive/10 border border-destructive/20 text-destructive text-xs font-medium">
              {error}
            </div>
          )}
        </div>

        {/* Brain status */}
        <div className="flex items-center justify-center gap-2 mt-6 text-xs text-text-tertiary">
          <span className="w-1.5 h-1.5 rounded-full bg-status-done animate-brain-pulse" />
          <span className="font-mono">brain online — monitoring clusters</span>
        </div>
      </div>
    </div>
  );
}
