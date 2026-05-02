"use client";

import { useEffect, useState } from "react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface Alert {
  id: string;
  scanner: string;
  check_id: string | null;
  severity: string;
  resource_kind: string | null;
  resource_namespace: string | null;
  resource_name: string | null;
  observed_at: string;
}

const SEVERITY_COLORS: Record<string, string> = {
  critical: "#ef4444", high: "#f97316", medium: "#eab308", low: "#6b7280", info: "#60a5fa",
};

export default function AlertsPage() {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`${API}/api/v1/alerts`)
      .then(r => r.json())
      .then(data => { setAlerts(data.items || []); setLoading(false); })
      .catch(() => setLoading(false));
  }, []);

  return (
    <div>
      <h1 style={{ fontSize: 20, fontWeight: 600, marginBottom: "var(--space-4)" }}>Alerts</h1>

      {loading && <div style={{ padding: "var(--space-8)", textAlign: "center", color: "var(--text-secondary)" }}>Loading...</div>}

      {!loading && alerts.length === 0 && (
        <div style={{ textAlign: "center", padding: "var(--space-8)", color: "var(--text-secondary)" }}>
          No active alerts.
        </div>
      )}

      {alerts.length > 0 && (
        <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-2)" }}>
          {alerts.map(a => (
            <div key={a.id} style={{
              background: "var(--bg-surface)",
              border: "1px solid var(--border-default)",
              borderRadius: 8,
              padding: "var(--space-3) var(--space-4)",
              borderLeft: `3px solid ${SEVERITY_COLORS[a.severity] || "var(--border-default)"}`,
            }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <div>
                  <span style={{ fontWeight: 600 }}>{a.scanner}</span>
                  {a.check_id && <span style={{ color: "var(--text-secondary)", marginLeft: "var(--space-2)" }}>/ {a.check_id}</span>}
                </div>
                <span style={{ fontSize: 11, padding: "2px 8px", borderRadius: 4, background: SEVERITY_COLORS[a.severity], color: "#fff", fontWeight: 600, textTransform: "uppercase" }}>
                  {a.severity}
                </span>
              </div>
              {a.resource_name && (
                <div style={{ fontSize: 13, color: "var(--text-secondary)", marginTop: "var(--space-1)" }}>
                  {a.resource_kind}/{a.resource_namespace}/{a.resource_name}
                </div>
              )}
              <div style={{ fontSize: 12, color: "var(--text-secondary)", marginTop: "var(--space-1)" }}>
                {new Date(a.observed_at).toLocaleString()}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
