"use client";

import { useEffect, useState } from "react";
import { useSearchParams, useRouter, usePathname } from "next/navigation";
import Link from "next/link";
import { Search, Brain } from "lucide-react";
import { api } from "@/lib/api";

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
    <header className="flex items-center justify-between h-12 px-5 border-b border-border-default bg-bg-surface">
      <div className="flex items-center gap-3">
        <select
          aria-label="Cluster selector"
          value={selectedCluster}
          onChange={e => handleClusterChange(e.target.value)}
          className="bg-bg-elevated text-text-primary border border-border-default rounded-md px-2 py-1 text-xs"
        >
          <option value="all">All Clusters ({clusters.length})</option>
          {clusters.map(c => <option key={c.id} value={c.id}>{c.display_name} ({c.onboarding_state})</option>)}
        </select>
        <button
          onClick={() => window.dispatchEvent(new KeyboardEvent("keydown", { key: "k", metaKey: true }))}
          className="flex items-center gap-2 px-3 py-1.5 bg-bg-elevated border border-border-default rounded-md text-text-tertiary text-xs cursor-pointer hover:border-border-focus transition-colors"
        >
          <Search size={14} />
          <span>Search...</span>
          <kbd className="font-mono text-[10px] px-1 py-0.5 rounded bg-bg-active text-text-tertiary ml-2">⌘K</kbd>
        </button>
      </div>
      <div className="flex items-center gap-4 text-xs">
        <div className="flex items-center gap-1.5 text-text-tertiary">
          <Brain size={14} className="text-accent-brain" />
          <span className="w-1.5 h-1.5 rounded-full bg-status-done" />
          <span>Brain active</span>
        </div>
        {session?.authenticated ? (
          <div className="flex items-center gap-1.5 text-text-secondary">
            <span className="w-1.5 h-1.5 rounded-full bg-status-done" />
            <span>{session.principal?.display_name || "Session active"}</span>
          </div>
        ) : session !== null ? (
          <Link href="/login" className="flex items-center gap-1.5 text-status-blocked no-underline">
            <span className="w-1.5 h-1.5 rounded-full bg-status-blocked" />
            <span>Session expired</span>
          </Link>
        ) : null}
      </div>
    </header>
  );
}
