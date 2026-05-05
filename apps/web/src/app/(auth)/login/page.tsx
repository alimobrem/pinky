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
    <div className="relative flex min-h-screen items-center justify-center overflow-hidden bg-bg-base">
      <div className="pointer-events-none absolute left-1/2 top-[45%] h-[600px] w-[800px] -translate-x-1/2 -translate-y-1/2 rounded-full bg-brand-purple/[0.07] blur-[180px]" />
      <div className="pointer-events-none absolute left-[40%] top-[55%] h-[400px] w-[600px] rounded-full bg-brand-pink/[0.05] blur-[140px]" />

      <div className="relative w-[420px] animate-fade-in">
        <div className="overflow-hidden rounded-2xl border border-border-default bg-bg-surface shadow-lg">
          <div className="flex flex-col items-center px-10 pb-6 pt-16">
            <div className="relative mb-8">
              <div className="absolute -inset-6 rounded-full bg-brand-purple/30 blur-2xl" />
              <div className="absolute -inset-3 rounded-full bg-brand-purple/20 blur-lg" />
              <Brain size={48} className="relative text-brand-purple drop-shadow-[0_0_16px_rgba(167,139,250,0.7)]" />
            </div>

            <h1 className="bg-gradient-to-r from-brand-pink to-brand-purple bg-clip-text text-3xl font-bold tracking-[0.16em] text-transparent">
              PINKY
            </h1>
            <p className="mt-4 text-sm text-text-tertiary">Multi-cluster ops.</p>
            <p className="mt-1.5 text-sm text-brand-purple/80">Powered by The Brain.</p>
          </div>

          <div className="mx-8 h-px bg-border-subtle" />

          <div className="flex flex-col gap-3.5 px-10 pb-10 pt-8">
            <Button
              className="h-12 w-full text-sm font-semibold tracking-wide"
              onClick={() => handleLogin("openshift")}
              disabled={loading !== null}
            >
              {loading === "openshift" ? "Redirecting..." : "Sign in with OpenShift"}
            </Button>
            <Button
              variant="outline"
              className="h-12 w-full text-sm tracking-wide"
              onClick={() => handleLogin("oidc")}
              disabled={loading !== null}
            >
              {loading === "oidc" ? "Redirecting..." : "Sign in with OIDC"}
            </Button>
          </div>

          {error && (
            <div className="mx-10 mb-8 rounded-lg border border-destructive/20 bg-destructive/10 p-3 text-xs text-destructive">
              {error}
            </div>
          )}
        </div>

        <div className="mt-10 flex items-center justify-center gap-2.5 text-xs text-text-tertiary">
          <span className="h-1.5 w-1.5 rounded-full bg-status-done animate-pulse-dot" />
          <span className="font-mono tracking-wider">brain online</span>
        </div>
      </div>
    </div>
  );
}
