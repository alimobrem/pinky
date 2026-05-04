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
      {/* Background ambient */}
      <div className="absolute top-[45%] left-[50%] -translate-x-1/2 -translate-y-1/2 w-[800px] h-[600px] rounded-full bg-accent-brain/[0.07] blur-[180px] pointer-events-none" />
      <div className="absolute top-[55%] left-[40%] w-[600px] h-[400px] rounded-full bg-accent-brand/[0.05] blur-[140px] pointer-events-none" />

      <div className="relative w-[380px] animate-fade-in">
        <div className="bg-card border border-border rounded-2xl shadow-elevated overflow-hidden">
          {/* Logo area */}
          <div className="flex flex-col items-center px-10 pt-14 pb-10">
            <div className="relative mb-8">
              <div className="absolute -inset-6 bg-accent-brain/30 blur-2xl rounded-full" />
              <div className="absolute -inset-3 bg-accent-brain/20 blur-lg rounded-full" />
              <Brain size={44} className="relative text-accent-brain drop-shadow-[0_0_16px_rgba(167,139,250,0.7)]" />
            </div>
            <h1 className="text-[28px] font-bold tracking-[0.14em] bg-gradient-to-r from-accent-brand to-accent-brain bg-clip-text text-transparent mb-3">
              PINKY
            </h1>
            <p className="text-text-tertiary text-sm">Multi-cluster ops.</p>
            <p className="text-accent-brain/80 text-sm mt-0.5">Powered by The Brain.</p>
          </div>

          {/* Actions */}
          <div className="px-8 pb-8 flex flex-col gap-3">
            <Button className="w-full h-11 text-sm font-semibold tracking-wide" onClick={() => handleLogin("openshift")} disabled={loading !== null}>
              {loading === "openshift" ? "Redirecting..." : "Sign in with OpenShift"}
            </Button>
            <Button variant="outline" className="w-full h-11 text-sm tracking-wide" onClick={() => handleLogin("oidc")} disabled={loading !== null}>
              {loading === "oidc" ? "Redirecting..." : "Sign in with OIDC"}
            </Button>
          </div>

          {error && (
            <div className="mx-8 mb-6 p-3 rounded-lg bg-destructive/10 border border-destructive/20 text-destructive text-xs">
              {error}
            </div>
          )}
        </div>

        {/* Status line */}
        <div className="flex items-center justify-center gap-2 mt-8 text-[11px] text-text-tertiary">
          <span className="w-1.5 h-1.5 rounded-full bg-status-done animate-brain-pulse" />
          <span className="font-mono tracking-wide">brain online — monitoring clusters</span>
        </div>
      </div>
    </div>
  );
}
