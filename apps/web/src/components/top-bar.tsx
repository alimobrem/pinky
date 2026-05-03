"use client";

import { useEffect, useState } from "react";
import { useSearchParams, useRouter, usePathname } from "next/navigation";
import Link from "next/link";
import { Search, Brain } from "lucide-react";
import css from "./top-bar.module.css";

const API = "";

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
    fetch(`${API}/api/v1/clusters`)
      .then(r => r.json())
      .then(d => setClusters(d.items || []))
      .catch(() => setClusters([]));
  }, []);

  useEffect(() => {
    const checkSession = () =>
      fetch(`${API}/api/v1/auth/session`, { credentials: "include" })
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
    <header className={css.bar}>
      <div className={css.left}>
        <select aria-label="Cluster selector" value={selectedCluster} onChange={e => handleClusterChange(e.target.value)} className={css.clusterSelect}>
          <option value="all">All Clusters ({clusters.length})</option>
          {clusters.map(c => <option key={c.id} value={c.id}>{c.display_name} ({c.onboarding_state})</option>)}
        </select>
        <button onClick={() => window.dispatchEvent(new KeyboardEvent("keydown", { key: "k", metaKey: true }))} className={css.searchBtn}>
          <Search size={14} />
          <span>Search...</span>
          <kbd className={css.searchKbd}>⌘K</kbd>
        </button>
      </div>
      <div className={css.right}>
        <div className={css.brainStatus}>
          <Brain size={14} style={{ color: "var(--accent-brain)" }} />
          <span className={css.brainDot} />
          <span>Brain active</span>
        </div>
        {session?.authenticated ? (
          <div className={css.sessionStatus}>
            <span className={css.sessionDot} />
            <span>{session.principal?.display_name || "Session active"}</span>
          </div>
        ) : session !== null ? (
          <Link href="/login" className={css.sessionExpired}>
            <span className={css.sessionDotExpired} />
            <span>Session expired</span>
          </Link>
        ) : null}
      </div>
    </header>
  );
}
