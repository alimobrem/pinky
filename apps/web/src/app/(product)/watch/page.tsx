"use client";

import { useEffect, useState } from "react";

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
    es.onopen = () => {
      setConnected(true);
      setLastUpdate(new Date().toLocaleTimeString());
    };
    es.addEventListener("heartbeat", () => {
      setConnected(true);
      setLastUpdate(new Date().toLocaleTimeString());
    });
    es.addEventListener("update", (e) => {
      setLastUpdate(new Date().toLocaleTimeString());
      fetch(`${API}/api/v1/issues?status=open`)
        .then(r => r.json())
        .then(data => setIssues(data.items || []));
    });
    es.onerror = () => setConnected(false);

    return () => es.close();
  }, []);

  const SEVERITY_COLORS: Record<string, string> = {
    critical: "#ef4444", high: "#f97316", medium: "#eab308", low: "#6b7280",
  };

  return (
    <div>
      <h1 style={{ fontSize: 20, fontWeight: 600, marginBottom: "var(--space-4)" }}>Watch</h1>

      <div style={{ display: "flex", alignItems: "center", gap: "var(--space-2)", marginBottom: "var(--space-6)", fontSize: 13, color: "var(--text-secondary)" }}>
        <span style={{ width: 8, height: 8, borderRadius: "50%", background: connected ? "var(--status-done)" : "var(--status-blocked)", display: "inline-block" }} />
        {connected ? `Live — updated ${lastUpdate}` : "Connecting..."}
      </div>

      {issues.length === 0 ? (
        <div style={{ textAlign: "center", padding: "var(--space-8)", color: "var(--text-secondary)" }}>
          The Brain is not actively escalating anything right now.
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-2)" }}>
          {issues.map(issue => (
            <div key={issue.id} style={{
              background: "var(--bg-surface)",
              border: "1px solid var(--border-default)",
              borderRadius: 8,
              padding: "var(--space-4)",
              borderLeft: `3px solid ${SEVERITY_COLORS[issue.severity] || "var(--border-default)"}`,
            }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <div style={{ fontWeight: 600 }}>{issue.title}</div>
                <span style={{ fontSize: 11, padding: "2px 8px", borderRadius: 4, background: SEVERITY_COLORS[issue.severity] || "#6b7280", color: "#fff", fontWeight: 600, textTransform: "uppercase" }}>
                  {issue.severity}
                </span>
              </div>
              <div style={{ fontSize: 12, color: "var(--text-secondary)", marginTop: "var(--space-1)" }}>
                {issue.status} — last seen {issue.last_seen_at ? new Date(issue.last_seen_at).toLocaleString() : "unknown"}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
