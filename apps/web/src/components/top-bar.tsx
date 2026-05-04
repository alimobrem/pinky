"use client";

import { useEffect, useState } from "react";
import { useSearchParams, useRouter, usePathname } from "next/navigation";
import Link from "next/link";
import { Search, Brain, ChevronDown, LogOut } from "lucide-react";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";

interface Cluster { id: string; display_name: string; onboarding_state: string; }
interface SessionInfo { authenticated: boolean; principal?: { display_name?: string }; }

export function TopBar() {
  const [clusters, setClusters] = useState<Cluster[]>([]);
  const [session, setSession] = useState<SessionInfo | null>(null);
  const searchParams = useSearchParams();
  const pathname = usePathname();
  const router = useRouter();
  const selectedCluster = searchParams.get("cluster") || "all";

  useEffect(() => {
    api.get<{ items: Cluster[] }>("/api/v1/clusters")
      .then(d => setClusters(d.items || []))
      .catch(() => setClusters([]));
  }, []);

  useEffect(() => {
    const checkSession = () =>
      fetch("/api/v1/auth/session", { credentials: "include" })
        .then(r => r.json())
        .then(setSession)
        .catch(() => setSession({ authenticated: false }));
    checkSession();
    const interval = setInterval(checkSession, 60000);
    return () => clearInterval(interval);
  }, []);

  const handleClusterChange = (value: string) => {
    const params = new URLSearchParams(searchParams.toString());
    if (value === "all") params.delete("cluster");
    else params.set("cluster", value);
    const qs = params.toString();
    router.replace(qs ? `${pathname}?${qs}` : pathname);
  };

  return (
    <header className="flex items-center justify-between h-12 px-5 border-b border-border-subtle bg-bg-primary">
      <div className="flex items-center gap-4">
        <div className="relative">
          <select
            aria-label="Cluster selector"
            value={selectedCluster}
            onChange={e => handleClusterChange(e.target.value)}
            className="appearance-none bg-bg-surface text-text-primary border border-border-default rounded-lg pl-3 pr-8 py-1.5 text-xs font-medium cursor-pointer hover:border-accent-brain/30 transition-colors focus:outline-none focus:ring-1 focus:ring-ring"
          >
            <option value="all">All Clusters ({clusters.length})</option>
            {clusters.map(c => <option key={c.id} value={c.id}>{c.display_name}</option>)}
          </select>
          <ChevronDown size={12} className="absolute right-2.5 top-1/2 -translate-y-1/2 text-text-tertiary pointer-events-none" />
        </div>
        <button
          onClick={() => window.dispatchEvent(new KeyboardEvent("keydown", { key: "k", metaKey: true }))}
          className="flex items-center gap-2 px-3 py-1.5 bg-bg-surface border border-border-default rounded-lg text-text-tertiary text-xs cursor-pointer hover:border-accent-brain/30 transition-colors"
        >
          <Search size={13} />
          <span className="text-text-tertiary">Search...</span>
          <kbd className="font-mono text-xs px-1.5 py-0.5 rounded bg-bg-active text-text-tertiary ml-4 border border-border-default">⌘K</kbd>
        </button>
      </div>
      <div className="flex items-center gap-5 text-xs">
        <div className="flex items-center gap-2 text-text-tertiary">
          <Brain size={13} className="text-accent-brain" />
          <span className="w-1.5 h-1.5 rounded-full bg-status-done animate-brain-pulse" />
          <span className="font-medium">Brain active</span>
        </div>
        {session?.authenticated ? (
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2 text-text-secondary font-medium">
              <span className="w-1.5 h-1.5 rounded-full bg-status-done" />
              <span>{session.principal?.display_name || "Connected"}</span>
            </div>
            <button
              onClick={async () => {
                await fetch("/api/v1/auth/logout", { method: "POST", credentials: "include" });
                window.location.href = "/login";
              }}
              className="text-text-tertiary hover:text-text-secondary transition-colors cursor-pointer bg-transparent border-none p-1"
              title="Sign out"
            >
              <LogOut size={13} />
            </button>
          </div>
        ) : session !== null ? (
          <Link href="/login" className={cn("flex items-center gap-2 no-underline font-medium", "text-status-blocked")}>
            <span className="w-1.5 h-1.5 rounded-full bg-status-blocked" />
            <span>Session expired</span>
          </Link>
        ) : null}
      </div>
    </header>
  );
}
