"use client";

import { useEffect, useState } from "react";
import { Settings as SettingsIcon, Plus, Trash2, Brain } from "lucide-react";
import { useToast } from "@/components/toast";

const API = "";

interface Cluster { id: string; display_name: string; api_endpoint: string; onboarding_state: string; }
interface Definition { id: string; kind: string; name: string; version: string; enabled: boolean; }
interface Webhook { id: string; name: string; url: string; formatter: string; enabled: boolean; }
interface PolicyRule { id: string; name: string; priority: number; enabled: boolean; }

export default function SettingsPage() {
  const [clusters, setClusters] = useState<Cluster[]>([]);
  const [definitions, setDefinitions] = useState<Definition[]>([]);
  const [webhooks, setWebhooks] = useState<Webhook[]>([]);
  const [rules, setRules] = useState<PolicyRule[]>([]);
  const [roi, setRoi] = useState<Record<string, unknown>>({});
  const [activeTab, setActiveTab] = useState("clusters");
  const { toast } = useToast();

  useEffect(() => {
    fetch(`${API}/api/v1/clusters`).then(r => r.json()).then(d => setClusters(d.items || [])).catch(() => {});
    fetch(`${API}/api/v1/definitions`).then(r => r.json()).then(d => setDefinitions(d.items || [])).catch(() => {});
    fetch(`${API}/api/v1/webhook-subscriptions`).then(r => r.json()).then(d => setWebhooks(d.items || [])).catch(() => {});
    fetch(`${API}/api/v1/policy-rules`).then(r => r.json()).then(d => setRules(d.items || [])).catch(() => {});
    fetch(`${API}/api/v1/analytics/roi`).then(r => r.json()).then(d => setRoi(d.metrics || {})).catch(() => {});
  }, []);

  const TABS = [
    { id: "clusters", label: "Clusters", count: clusters.length },
    { id: "definitions", label: "Definitions", count: definitions.length },
    { id: "webhooks", label: "Webhooks", count: webhooks.length },
    { id: "rules", label: "Policy Rules", count: rules.length },
    { id: "analytics", label: "Analytics / ROI", count: null },
  ];

  const deleteCluster = async (id: string) => {
    const r = await fetch(`${API}/api/v1/clusters/${id}`, { method: "DELETE" });
    if (r.ok) { setClusters(c => c.filter(x => x.id !== id)); toast("Cluster removed", "success"); }
    else toast("Failed to remove cluster", "error");
  };

  return (
    <div>
      <div style={{ display: "flex", alignItems: "center", gap: "var(--space-3)", marginBottom: "var(--space-5)" }}>
        <SettingsIcon size={20} style={{ color: "var(--text-tertiary)" }} />
        <h1 style={{ fontSize: 20, fontWeight: 600, letterSpacing: "-0.01em" }}>Settings</h1>
      </div>

      {/* Tabs */}
      <div style={{ display: "flex", gap: "var(--space-1)", marginBottom: "var(--space-5)", borderBottom: "1px solid var(--border-subtle)", paddingBottom: "var(--space-1)" }}>
        {TABS.map(tab => (
          <button key={tab.id} onClick={() => setActiveTab(tab.id)} style={{
            padding: "var(--space-2) var(--space-4)", fontSize: 13, fontWeight: activeTab === tab.id ? 600 : 400,
            color: activeTab === tab.id ? "var(--text-primary)" : "var(--text-secondary)",
            background: activeTab === tab.id ? "var(--bg-elevated)" : "transparent",
            border: "none", borderRadius: "var(--radius-md) var(--radius-md) 0 0", cursor: "pointer",
            transition: "color var(--transition-fast), background var(--transition-fast)",
          }}>
            {tab.label}
            {tab.count != null && (
              <span style={{ marginLeft: "var(--space-2)", fontSize: 11, color: "var(--text-tertiary)" }}>({tab.count})</span>
            )}
          </button>
        ))}
      </div>

      {/* Clusters Tab */}
      {activeTab === "clusters" && (
        <div>
          {clusters.length === 0 ? (
            <div style={{ textAlign: "center", padding: "var(--space-10)", color: "var(--text-secondary)" }}>
              No clusters registered. <button style={{ color: "var(--accent-brand)", background: "none", border: "none", cursor: "pointer", fontWeight: 600 }}>+ Add first cluster</button>
            </div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-2)" }}>
              {clusters.map(c => (
                <div key={c.id} style={{
                  background: "var(--bg-surface)", border: "1px solid var(--border-default)",
                  borderRadius: "var(--radius-lg)", padding: "var(--space-3) var(--space-5)",
                  display: "flex", justifyContent: "space-between", alignItems: "center",
                }}>
                  <div>
                    <div style={{ fontWeight: 600, fontSize: 14 }}>{c.display_name}</div>
                    <div style={{ fontSize: 12, color: "var(--text-tertiary)", fontFamily: "var(--font-mono)" }}>{c.api_endpoint}</div>
                  </div>
                  <div style={{ display: "flex", alignItems: "center", gap: "var(--space-3)" }}>
                    <span style={{ fontSize: 11, padding: "2px 8px", borderRadius: "var(--radius-sm)", background: c.onboarding_state === "ready" ? "var(--status-done)" : "var(--status-in-progress)", color: "#fff", fontWeight: 600 }}>
                      {c.onboarding_state}
                    </span>
                    <button onClick={() => deleteCluster(c.id)} style={{
                      background: "none", border: "none", color: "var(--text-tertiary)", cursor: "pointer",
                    }}><Trash2 size={14} /></button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Definitions Tab */}
      {activeTab === "definitions" && (
        <div>
          {definitions.length === 0 ? (
            <div style={{ textAlign: "center", padding: "var(--space-10)", color: "var(--text-secondary)" }}>No definitions in DB. Built-in definitions are loaded from the filesystem.</div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-2)" }}>
              {definitions.map(d => (
                <div key={d.id} style={{
                  background: "var(--bg-surface)", border: "1px solid var(--border-default)",
                  borderRadius: "var(--radius-lg)", padding: "var(--space-3) var(--space-5)",
                  display: "flex", justifyContent: "space-between", alignItems: "center",
                }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "var(--space-3)" }}>
                    <span style={{ fontSize: 11, padding: "2px 6px", borderRadius: "var(--radius-sm)", background: "var(--bg-elevated)", textTransform: "uppercase", fontWeight: 600, color: "var(--text-tertiary)" }}>{d.kind}</span>
                    <span style={{ fontWeight: 600 }}>{d.name}</span>
                    <span style={{ fontSize: 12, color: "var(--text-tertiary)" }}>v{d.version}</span>
                  </div>
                  <span style={{ fontSize: 12, color: d.enabled ? "var(--status-done)" : "var(--text-tertiary)" }}>
                    {d.enabled ? "Enabled" : "Disabled"}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Webhooks Tab */}
      {activeTab === "webhooks" && (
        <div>
          {webhooks.length === 0 ? (
            <div style={{ textAlign: "center", padding: "var(--space-10)", color: "var(--text-secondary)" }}>No webhook subscriptions. Create one to receive notifications.</div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-2)" }}>
              {webhooks.map(w => (
                <div key={w.id} style={{
                  background: "var(--bg-surface)", border: "1px solid var(--border-default)",
                  borderRadius: "var(--radius-lg)", padding: "var(--space-3) var(--space-5)",
                  display: "flex", justifyContent: "space-between", alignItems: "center",
                }}>
                  <div>
                    <div style={{ fontWeight: 600, fontSize: 14 }}>{w.name}</div>
                    <div style={{ fontSize: 12, color: "var(--text-tertiary)", fontFamily: "var(--font-mono)" }}>{w.url}</div>
                  </div>
                  <span style={{ fontSize: 11, padding: "2px 6px", borderRadius: "var(--radius-sm)", background: "var(--bg-elevated)", textTransform: "uppercase", fontWeight: 600, color: "var(--text-tertiary)" }}>{w.formatter}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Policy Rules Tab */}
      {activeTab === "rules" && (
        <div>
          {rules.length === 0 ? (
            <div style={{ textAlign: "center", padding: "var(--space-10)", color: "var(--text-secondary)" }}>No policy rules configured. Rules are loaded from definitions/policies/ directory.</div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-2)" }}>
              {rules.map(r => (
                <div key={r.id} style={{
                  background: "var(--bg-surface)", border: "1px solid var(--border-default)",
                  borderRadius: "var(--radius-lg)", padding: "var(--space-3) var(--space-5)",
                  display: "flex", justifyContent: "space-between", alignItems: "center",
                }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "var(--space-3)" }}>
                    <span className="tabular" style={{ fontSize: 12, color: "var(--text-tertiary)", fontWeight: 600, minWidth: 30 }}>#{r.priority}</span>
                    <span style={{ fontWeight: 600 }}>{r.name}</span>
                  </div>
                  <span style={{ fontSize: 12, color: r.enabled ? "var(--status-done)" : "var(--text-tertiary)" }}>
                    {r.enabled ? "Active" : "Inactive"}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Analytics Tab */}
      {activeTab === "analytics" && (
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: "var(--space-2)", marginBottom: "var(--space-4)" }}>
            <Brain size={16} style={{ color: "var(--accent-brain)" }} />
            <span style={{ fontSize: 14, fontWeight: 600 }}>ROI Metrics</span>
          </div>
          {Object.keys(roi).length === 0 ? (
            <div style={{ textAlign: "center", padding: "var(--space-10)", color: "var(--text-secondary)" }}>No analytics data yet. Metrics will populate as Pinky processes issues.</div>
          ) : (
            <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "var(--space-4)" }}>
              {Object.entries(roi).map(([k, v]) => (
                <div key={k} style={{
                  background: "var(--bg-surface)", border: "1px solid var(--border-default)",
                  borderRadius: "var(--radius-lg)", padding: "var(--space-4)",
                }}>
                  <div className="tabular" style={{ fontSize: 28, fontWeight: 700, lineHeight: 1 }}>{String(v ?? "—")}</div>
                  <div style={{ fontSize: 12, color: "var(--text-tertiary)", marginTop: "var(--space-1)", textTransform: "capitalize" }}>
                    {k.replace(/_/g, " ")}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
