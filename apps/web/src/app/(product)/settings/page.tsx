"use client";

import { useEffect, useState } from "react";

const API = "";

interface Section {
  title: string;
  desc: string;
  endpoint: string;
  countField?: string;
}

const SECTIONS: Section[] = [
  { title: "Cluster Registry", desc: "Manage registered clusters and observer bindings", endpoint: "/api/v1/clusters" },
  { title: "Cluster Bindings", desc: "Your cluster access and binding status", endpoint: "/api/v1/cluster-bindings" },
  { title: "Service Bindings", desc: "External service connections (Prometheus, Datadog)", endpoint: "/api/v1/service-bindings" },
  { title: "Definitions", desc: "Scanners, tools, skills, pipelines, and policies", endpoint: "/api/v1/definitions" },
  { title: "Webhooks", desc: "Outbound notification subscriptions", endpoint: "/api/v1/webhook-subscriptions" },
  { title: "Policy Rules", desc: "Declarative triage rules", endpoint: "/api/v1/policy-rules" },
];

export default function SettingsPage() {
  const [counts, setCounts] = useState<Record<string, number>>({});
  const [roi, setRoi] = useState<Record<string, unknown>>({});

  useEffect(() => {
    for (const s of SECTIONS) {
      fetch(`${API}${s.endpoint}`)
        .then(r => r.json())
        .then(data => setCounts(prev => ({ ...prev, [s.title]: (data.items || []).length })))
        .catch(() => {});
    }

    fetch(`${API}/api/v1/analytics/roi`)
      .then(r => r.json())
      .then(data => setRoi(data.metrics || {}))
      .catch(() => {});
  }, []);

  return (
    <div>
      <h1 style={{ fontSize: 20, fontWeight: 600, marginBottom: "var(--space-6)" }}>Settings</h1>

      <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-4)" }}>
        {SECTIONS.map(s => (
          <div key={s.title} style={{
            background: "var(--bg-surface)",
            border: "1px solid var(--border-default)",
            borderRadius: 8,
            padding: "var(--space-4)",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}>
            <div>
              <div style={{ fontWeight: 600, marginBottom: "var(--space-1)" }}>{s.title}</div>
              <div style={{ fontSize: 13, color: "var(--text-secondary)" }}>{s.desc}</div>
            </div>
            {counts[s.title] !== undefined && (
              <span style={{ fontSize: 20, fontWeight: 700, color: "var(--text-secondary)" }}>
                {counts[s.title]}
              </span>
            )}
          </div>
        ))}

        <div style={{
          background: "var(--bg-surface)",
          border: "1px solid var(--border-default)",
          borderRadius: 8,
          padding: "var(--space-4)",
        }}>
          <div style={{ fontWeight: 600, marginBottom: "var(--space-3)" }}>Analytics / ROI</div>
          {Object.keys(roi).length === 0 ? (
            <div style={{ fontSize: 13, color: "var(--text-secondary)" }}>Loading metrics...</div>
          ) : (
            <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "var(--space-3)" }}>
              {Object.entries(roi).map(([k, v]) => (
                <div key={k}>
                  <div style={{ fontSize: 20, fontWeight: 700 }}>{String(v ?? "-")}</div>
                  <div style={{ fontSize: 12, color: "var(--text-secondary)" }}>{k.replace(/_/g, " ")}</div>
                </div>
              ))}
            </div>
          )}
        </div>

        <div style={{
          background: "var(--bg-surface)",
          border: "1px solid var(--border-default)",
          borderRadius: 8,
          padding: "var(--space-4)",
        }}>
          <div style={{ fontWeight: 600, marginBottom: "var(--space-1)" }}>Profile</div>
          <div style={{ fontSize: 13, color: "var(--text-secondary)" }}>Your account, linked providers, and active sessions</div>
        </div>
      </div>
    </div>
  );
}
