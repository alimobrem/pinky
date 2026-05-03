"use client";

import { useEffect, useState } from "react";
import { Brain, Eye } from "lucide-react";

const API = "";

interface Issue {
  id: string;
  title: string;
  severity: string;
  status: string;
  cluster_id: string;
  correlation_key: string;
  last_seen_at: string;
}

const SEVERITY_COLORS: Record<string, string> = {
  critical: "var(--priority-critical)", high: "var(--priority-high)",
  medium: "var(--priority-medium)", low: "var(--priority-low)", info: "var(--status-ready)",
};

export default function WatchPage() {
  const [issues, setIssues] = useState<Issue[]>([]);
  const [connected, setConnected] = useState(false);
  const [lastUpdate, setLastUpdate] = useState<string>("");

  useEffect(() => {
    fetch(`${API}/api/v1/issues?status=open`)
      .then(r => r.json())
      .then(data => setIssues(data.items || []))
      .catch(() => {});

    const es = new EventSource(`${API}/api/v1/streams/watch`);
    es.onopen = () => { setConnected(true); setLastUpdate(new Date().toLocaleTimeString()); };
    es.addEventListener("heartbeat", () => { setConnected(true); setLastUpdate(new Date().toLocaleTimeString()); });
    es.addEventListener("update", () => {
      setLastUpdate(new Date().toLocaleTimeString());
      fetch(`${API}/api/v1/issues?status=open`).then(r => r.json()).then(data => setIssues(data.items || []));
    });
    es.onerror = () => setConnected(false);
    return () => es.close();
  }, []);

  return (
    <div>
      <div style={{ display: "flex", alignItems: "center", gap: "var(--space-3)", marginBottom: "var(--space-5)" }}>
        <Eye size={20} style={{ color: "var(--text-tertiary)" }} />
        <h1 style={{ fontSize: 20, fontWeight: 600, letterSpacing: "-0.01em" }}>Watch</h1>
      </div>

      <div style={{ display: "flex", alignItems: "center", gap: "var(--space-2)", marginBottom: "var(--space-6)", fontSize: 12, color: "var(--text-tertiary)" }}>
        <span style={{
          width: 8, height: 8, borderRadius: "50%",
          background: connected ? "var(--status-done)" : "var(--status-blocked)",
          display: "inline-block",
          animation: connected ? "brain-pulse 2s ease-in-out infinite" : "none",
        }} />
        {connected ? `Live — updated ${lastUpdate}` : "Connecting..."}
      </div>

      {issues.length === 0 ? (
        <div style={{ display: "flex", flexDirection: "column", alignItems: "center", padding: "var(--space-16) var(--space-6)", textAlign: "center" }}>
          <div style={{ fontFamily: "var(--font-mono)", fontSize: 20, color: "var(--text-tertiary)", marginBottom: "var(--space-6)" }}>~ ~ ~</div>
          <div style={{ fontSize: 15, fontWeight: 600, color: "var(--text-primary)", marginBottom: "var(--space-2)" }}>All quiet on the western cluster.</div>
          <div style={{ fontSize: 13, color: "var(--text-secondary)", lineHeight: 1.6 }}>The Brain is monitoring but has nothing to escalate right now.</div>
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-2)" }}>
          {issues.map(issue => (
            <div key={issue.id} style={{
              background: "var(--bg-surface)", border: "1px solid var(--border-default)",
              borderRadius: "var(--radius-lg)", padding: "var(--space-4) var(--space-5)",
              borderLeft: `3px solid ${SEVERITY_COLORS[issue.severity] || "var(--border-default)"}`,
              transition: "background var(--transition-fast)",
            }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "var(--space-2)" }}>
                  <Brain size={14} style={{ color: "var(--accent-brain)" }} />
                  <span style={{ fontWeight: 600, fontSize: 14 }}>{issue.title}</span>
                </div>
                <span style={{
                  fontSize: 11, padding: "2px 8px", borderRadius: "var(--radius-sm)",
                  background: SEVERITY_COLORS[issue.severity], color: "#fff", fontWeight: 600, textTransform: "uppercase",
                }}>{issue.severity}</span>
              </div>
              <div style={{ fontSize: 12, color: "var(--text-tertiary)", marginTop: "var(--space-2)", paddingLeft: "var(--space-6)" }}>
                {issue.status} — last seen {issue.last_seen_at ? new Date(issue.last_seen_at).toLocaleString() : "unknown"}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
