"use client";

import { useEffect, useState } from "react";
import { Search, Brain } from "lucide-react";

const API = "";

interface Cluster {
  id: string;
  display_name: string;
  onboarding_state: string;
}

export function TopBar() {
  const [clusters, setClusters] = useState<Cluster[]>([]);
  const [selectedCluster, setSelectedCluster] = useState("all");

  useEffect(() => {
    fetch(`${API}/api/v1/clusters`)
      .then(r => r.json())
      .then(d => setClusters(d.items || []))
      .catch(() => {});
  }, []);

  return (
    <header style={{
      height: 52, background: "var(--bg-surface)",
      borderBottom: "1px solid var(--border-default)",
      display: "flex", alignItems: "center", justifyContent: "space-between",
      padding: "0 var(--space-5)",
    }}>
      <div style={{ display: "flex", alignItems: "center", gap: "var(--space-4)" }}>
        <select
          aria-label="Cluster selector"
          value={selectedCluster}
          onChange={e => setSelectedCluster(e.target.value)}
          style={{
            background: "var(--bg-elevated)", color: "var(--text-primary)",
            border: "1px solid var(--border-default)", borderRadius: "var(--radius-md)",
            padding: "6px 12px", fontSize: 13, fontWeight: 500, cursor: "pointer",
          }}
        >
          <option value="all">All Clusters ({clusters.length})</option>
          {clusters.map(c => (
            <option key={c.id} value={c.id}>
              {c.display_name} ({c.onboarding_state})
            </option>
          ))}
        </select>

        <button
          onClick={() => {
            const event = new KeyboardEvent("keydown", { key: "k", metaKey: true });
            window.dispatchEvent(event);
          }}
          style={{
            display: "flex", alignItems: "center", gap: "var(--space-2)",
            background: "var(--bg-elevated)", border: "1px solid var(--border-default)",
            borderRadius: "var(--radius-md)", padding: "6px 12px",
            fontSize: 12, color: "var(--text-tertiary)", cursor: "pointer",
          }}
        >
          <Search size={14} />
          <span>Search...</span>
          <kbd style={{
            background: "var(--bg-active)", borderRadius: "var(--radius-sm)",
            padding: "1px 6px", fontSize: 11, fontWeight: 600, marginLeft: "var(--space-3)",
          }}>⌘K</kbd>
        </button>
      </div>

      <div style={{ display: "flex", alignItems: "center", gap: "var(--space-4)" }}>
        <div style={{
          display: "flex", alignItems: "center", gap: "var(--space-2)",
          fontSize: 12, color: "var(--text-tertiary)",
        }}>
          <Brain size={14} style={{ color: "var(--accent-brain)" }} />
          <span style={{
            width: 6, height: 6, borderRadius: "50%",
            background: "var(--accent-brain)", display: "inline-block",
            animation: "brain-pulse 2s ease-in-out infinite",
          }} />
          <span>Brain active</span>
        </div>

        <div style={{
          display: "flex", alignItems: "center", gap: "var(--space-2)",
          fontSize: 13, color: "var(--text-secondary)",
        }}>
          <span style={{
            width: 8, height: 8, borderRadius: "50%",
            background: "var(--status-done)", display: "inline-block",
          }} />
          <span>Session active</span>
        </div>
      </div>
    </header>
  );
}
