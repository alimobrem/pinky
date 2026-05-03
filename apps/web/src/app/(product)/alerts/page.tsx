"use client";

import { useEffect, useState } from "react";
import { AlertTriangle, Filter } from "lucide-react";

const API = "";

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
  critical: "var(--priority-critical)", high: "var(--priority-high)",
  medium: "var(--priority-medium)", low: "var(--priority-low)", info: "var(--status-ready)",
};

export default function AlertsPage() {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [loading, setLoading] = useState(true);
  const [severityFilter, setSeverityFilter] = useState("");

  useEffect(() => {
    fetch(`${API}/api/v1/alerts`)
      .then(r => r.json())
      .then(data => { setAlerts(data.items || []); setLoading(false); })
      .catch(() => setLoading(false));
  }, []);

  const filtered = severityFilter ? alerts.filter(a => a.severity === severityFilter) : alerts;

  return (
    <div>
      <div style={{ display: "flex", alignItems: "center", gap: "var(--space-3)", marginBottom: "var(--space-5)" }}>
        <AlertTriangle size={20} style={{ color: "var(--text-tertiary)" }} />
        <h1 style={{ fontSize: 20, fontWeight: 600, letterSpacing: "-0.01em" }}>Alerts</h1>
      </div>

      <div style={{ display: "flex", gap: "var(--space-3)", marginBottom: "var(--space-4)", alignItems: "center" }}>
        <Filter size={14} style={{ color: "var(--text-tertiary)" }} />
        <select value={severityFilter} onChange={e => setSeverityFilter(e.target.value)} style={{
          background: "var(--bg-elevated)", color: "var(--text-primary)", border: "1px solid var(--border-default)",
          borderRadius: "var(--radius-md)", padding: "4px 8px", fontSize: 12,
        }}>
          <option value="">All Severities</option>
          <option value="critical">Critical</option>
          <option value="high">High</option>
          <option value="medium">Medium</option>
          <option value="low">Low</option>
        </select>
        <span style={{ marginLeft: "auto", fontSize: 12, color: "var(--text-tertiary)" }}>{filtered.length} alerts</span>
      </div>

      {loading && (
        <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-2)" }}>
          {[1, 2, 3].map(i => <div key={i} className="skeleton" style={{ height: 64, borderRadius: "var(--radius-lg)" }} />)}
        </div>
      )}

      {!loading && filtered.length === 0 && (
        <div style={{ display: "flex", flexDirection: "column", alignItems: "center", padding: "var(--space-16) var(--space-6)", textAlign: "center" }}>
          <div style={{ fontFamily: "var(--font-mono)", fontSize: 20, color: "var(--text-tertiary)", marginBottom: "var(--space-6)" }}>(clear)</div>
          <div style={{ fontSize: 15, fontWeight: 600, marginBottom: "var(--space-2)" }}>No active alerts.</div>
          <div style={{ fontSize: 13, color: "var(--text-secondary)", lineHeight: 1.6 }}>Raw signals from your observability stack will appear here when detected.</div>
        </div>
      )}

      {filtered.length > 0 && (
        <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-2)" }}>
          {filtered.map(a => (
            <div key={a.id} style={{
              background: "var(--bg-surface)", border: "1px solid var(--border-default)",
              borderRadius: "var(--radius-lg)", padding: "var(--space-3) var(--space-5)",
              borderLeft: `3px solid ${SEVERITY_COLORS[a.severity] || "var(--border-default)"}`,
            }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "var(--space-3)" }}>
                  <span style={{ fontWeight: 600, fontSize: 14 }}>{a.scanner}</span>
                  {a.check_id && <span style={{ color: "var(--text-tertiary)", fontSize: 13 }}>/ {a.check_id}</span>}
                </div>
                <span style={{
                  fontSize: 11, padding: "2px 8px", borderRadius: "var(--radius-sm)",
                  background: SEVERITY_COLORS[a.severity], color: "#fff", fontWeight: 600, textTransform: "uppercase",
                }}>{a.severity}</span>
              </div>
              {a.resource_name && (
                <div style={{ fontSize: 13, color: "var(--text-secondary)", marginTop: "var(--space-1)" }}>
                  <span style={{ fontFamily: "var(--font-mono)", fontSize: 12 }}>
                    {a.resource_kind}/{a.resource_namespace}/{a.resource_name}
                  </span>
                </div>
              )}
              <div style={{ fontSize: 11, color: "var(--text-tertiary)", marginTop: "var(--space-1)", fontVariantNumeric: "tabular-nums" }}>
                {new Date(a.observed_at).toLocaleString()}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
