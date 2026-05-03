"use client";

import { useEffect, useState } from "react";
import { Search, Brain } from "lucide-react";
import css from "./top-bar.module.css";

const API = "";

interface Cluster { id: string; display_name: string; onboarding_state: string; }

export function TopBar() {
  const [clusters, setClusters] = useState<Cluster[]>([]);
  const [selectedCluster, setSelectedCluster] = useState("all");

  useEffect(() => {
    fetch(`${API}/api/v1/clusters`).then(r => r.json()).then(d => setClusters(d.items || [])).catch(() => {});
  }, []);

  return (
    <header className={css.bar}>
      <div className={css.left}>
        <select aria-label="Cluster selector" value={selectedCluster} onChange={e => setSelectedCluster(e.target.value)} className={css.clusterSelect}>
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
        <div className={css.sessionStatus}>
          <span className={css.sessionDot} />
          <span>Session active</span>
        </div>
      </div>
    </header>
  );
}
