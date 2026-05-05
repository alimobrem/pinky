"use client";

import { useState } from "react";
import { Settings as SettingsIcon, Plus, Trash2, Brain } from "lucide-react";
import { toast } from "sonner";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import type { ClusterRegistryEntry, ClusterIdentityBinding, Definition, WebhookSubscription, PolicyRule, PaginatedResponse } from "@pinky/contracts";
import { PageHeader } from "@/components/page-header";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from "@/components/ui/alert-dialog";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { api } from "@/lib/api";

export default function SettingsPage() {
  const queryClient = useQueryClient();

  const { data: clustersData } = useQuery({ queryKey: ["clusters"], queryFn: () => api.get<PaginatedResponse<ClusterRegistryEntry>>("/api/v1/clusters") });
  const { data: defsData } = useQuery({ queryKey: ["definitions"], queryFn: () => api.get<PaginatedResponse<Definition>>("/api/v1/definitions") });
  const { data: webhooksData } = useQuery({ queryKey: ["webhooks"], queryFn: () => api.get<PaginatedResponse<WebhookSubscription>>("/api/v1/webhook-subscriptions") });
  const { data: rulesData } = useQuery({ queryKey: ["rules"], queryFn: () => api.get<PaginatedResponse<PolicyRule>>("/api/v1/policy-rules") });
  const { data: roiData } = useQuery({ queryKey: ["analytics-roi"], queryFn: () => api.get<{ metrics: Record<string, unknown> }>("/api/v1/analytics/roi") });

  const { data: bindingsData } = useQuery({ queryKey: ["bindings"], queryFn: () => api.get<{ items: ClusterIdentityBinding[] }>("/api/v1/cluster-bindings") });

  const clusters = clustersData?.items ?? [];
  const bindings = bindingsData?.items ?? [];
  const definitions = defsData?.items ?? [];
  const webhooks = webhooksData?.items ?? [];
  const rules = rulesData?.items ?? [];
  const roi = roiData?.metrics ?? {};

  const [clusterOpen, setClusterOpen] = useState(false);
  const [clusterForm, setClusterForm] = useState({ display_name: "", api_endpoint: "", fleet_identifier: "" });
  const [defOpen, setDefOpen] = useState(false);
  const [defForm, setDefForm] = useState({ kind: "scanner", name: "", version: "1", frontmatter: "{}", body: "" });
  const [webhookOpen, setWebhookOpen] = useState(false);
  const [webhookForm, setWebhookForm] = useState({ name: "", url: "", event_patterns: "", formatter: "generic" });
  const [ruleOpen, setRuleOpen] = useState(false);
  const [ruleForm, setRuleForm] = useState({ name: "", description: "", priority: "50", conditions: "{}", action: "{}" });
  const [deleteTarget, setDeleteTarget] = useState<{ id: string; type: string; label: string } | null>(null);
  const [bindingClusterId, setBindingClusterId] = useState("");

  const refresh = () => {
    queryClient.invalidateQueries({ queryKey: ["clusters"] });
    queryClient.invalidateQueries({ queryKey: ["definitions"] });
    queryClient.invalidateQueries({ queryKey: ["webhooks"] });
    queryClient.invalidateQueries({ queryKey: ["rules"] });
    queryClient.invalidateQueries({ queryKey: ["bindings"] });
    queryClient.invalidateQueries({ queryKey: ["analytics-roi"] });
  };

  const createCluster = async () => {
    try {
      await api.post("/api/v1/clusters", { display_name: clusterForm.display_name, api_endpoint: clusterForm.api_endpoint, fleet_identifier: clusterForm.fleet_identifier || null });
      toast.success("Cluster added");
      setClusterOpen(false);
      setClusterForm({ display_name: "", api_endpoint: "", fleet_identifier: "" });
      refresh();
    } catch (e) { toast.error(e instanceof Error ? e.message : "Failed"); }
  };

  const createDefinition = async () => {
    try {
      let frontmatter = {};
      try { frontmatter = JSON.parse(defForm.frontmatter); } catch { toast.error("Invalid frontmatter JSON"); return; }
      await api.post("/api/v1/definitions", { kind: defForm.kind, name: defForm.name, version: defForm.version, frontmatter, body: defForm.body, enabled: true });
      toast.success("Definition created");
      setDefOpen(false);
      setDefForm({ kind: "scanner", name: "", version: "1", frontmatter: "{}", body: "" });
      refresh();
    } catch (e) { toast.error(e instanceof Error ? e.message : "Failed"); }
  };

  const createWebhook = async () => {
    try {
      await api.post("/api/v1/webhook-subscriptions", { name: webhookForm.name, url: webhookForm.url, event_patterns: webhookForm.event_patterns.split(",").map(s => s.trim()).filter(Boolean), formatter: webhookForm.formatter });
      toast.success("Webhook created");
      setWebhookOpen(false);
      setWebhookForm({ name: "", url: "", event_patterns: "", formatter: "generic" });
      refresh();
    } catch (e) { toast.error(e instanceof Error ? e.message : "Failed"); }
  };

  const createRule = async () => {
    try {
      let conditions = {}, action = {};
      try { conditions = JSON.parse(ruleForm.conditions); } catch { toast.error("Invalid conditions JSON"); return; }
      try { action = JSON.parse(ruleForm.action); } catch { toast.error("Invalid action JSON"); return; }
      await api.post("/api/v1/policy-rules", { name: ruleForm.name, description: ruleForm.description || null, priority: parseInt(ruleForm.priority, 10), conditions, action });
      toast.success("Rule created");
      setRuleOpen(false);
      setRuleForm({ name: "", description: "", priority: "50", conditions: "{}", action: "{}" });
      refresh();
    } catch (e) { toast.error(e instanceof Error ? e.message : "Failed"); }
  };

  const handleDelete = async () => {
    if (!deleteTarget) return;
    try {
      if (deleteTarget.type === "cluster") await api.del(`/api/v1/clusters/${deleteTarget.id}`);
      else if (deleteTarget.type === "definition") await api.del(`/api/v1/definitions/${deleteTarget.id}`);
      else if (deleteTarget.type === "webhook") await api.del(`/api/v1/webhook-subscriptions/${deleteTarget.id}`);
      else if (deleteTarget.type === "rule") await api.del(`/api/v1/policy-rules/${deleteTarget.id}`);
      else if (deleteTarget.type === "binding") await api.del(`/api/v1/cluster-bindings/${deleteTarget.id}`);
      toast.success(`${deleteTarget.type} deleted`);
      refresh();
    } catch { toast.error("Failed to delete"); }
    setDeleteTarget(null);
  };

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="System configuration"
        title="Settings"
        description="Manage clusters, bindings, definitions, notification plumbing, and the platform rules that shape how The Brain behaves."
        meta={
          <>
            <span>{clusters.length} clusters</span>
            <span>{bindings.length} bindings</span>
            <span>{definitions.length} definitions</span>
            <span>{rules.length} policy rules</span>
          </>
        }
      />

      <Tabs defaultValue="clusters">
        <div className="mt-8 rounded-2xl border border-border-default bg-bg-surface p-5 shadow-card sm:p-6">
          <div className="mb-4 flex items-center gap-2 text-sm font-semibold text-text-primary">
            <SettingsIcon size={16} className="text-text-tertiary" />
            Configuration areas
          </div>
          <div className="overflow-x-auto pb-1">
            <TabsList className="min-w-max justify-start gap-1.5 rounded-xl border border-border-default bg-bg-elevated p-1.5">
              <TabsTrigger value="clusters" className="px-4 py-2 text-sm">Clusters ({clusters.length})</TabsTrigger>
              <TabsTrigger value="definitions" className="px-4 py-2 text-sm">Definitions ({definitions.length})</TabsTrigger>
              <TabsTrigger value="webhooks" className="px-4 py-2 text-sm">Webhooks ({webhooks.length})</TabsTrigger>
              <TabsTrigger value="rules" className="px-4 py-2 text-sm">Policy Rules ({rules.length})</TabsTrigger>
              <TabsTrigger value="access" className="px-4 py-2 text-sm">Cluster Access ({bindings.length})</TabsTrigger>
              <TabsTrigger value="analytics" className="px-4 py-2 text-sm">Analytics / ROI</TabsTrigger>
            </TabsList>
          </div>
        </div>

        {/* Clusters */}
        <TabsContent value="clusters" className="mt-6 rounded-2xl border border-border-default bg-bg-surface p-5 shadow-card sm:p-6">
          <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <span className="text-sm font-semibold text-text-secondary">Registered Clusters</span>
            <Dialog open={clusterOpen} onOpenChange={setClusterOpen}>
              <DialogTrigger asChild>
                <Button size="sm" className="shrink-0"><Plus size={14} /> Add</Button>
              </DialogTrigger>
              <DialogContent>
                <DialogHeader><DialogTitle>Add Cluster</DialogTitle></DialogHeader>
                <div className="flex flex-col gap-4">
                  <div className="space-y-2">
                    <Label>Display Name *</Label>
                    <Input value={clusterForm.display_name} onChange={e => setClusterForm(f => ({ ...f, display_name: e.target.value }))} placeholder="my-cluster" />
                  </div>
                  <div className="space-y-2">
                    <Label>API Endpoint *</Label>
                    <Input value={clusterForm.api_endpoint} onChange={e => setClusterForm(f => ({ ...f, api_endpoint: e.target.value }))} placeholder="https://api.cluster.example.com:6443" />
                  </div>
                  <div className="space-y-2">
                    <Label>Fleet Identifier</Label>
                    <Input value={clusterForm.fleet_identifier} onChange={e => setClusterForm(f => ({ ...f, fleet_identifier: e.target.value }))} placeholder="Optional — ACM/OCM identifier" />
                  </div>
                </div>
                <DialogFooter>
                  <Button variant="outline" onClick={() => setClusterOpen(false)}>Cancel</Button>
                  <Button onClick={createCluster} disabled={!clusterForm.display_name || !clusterForm.api_endpoint}>Add Cluster</Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>
          </div>
          {clusters.length === 0 ? (
            <div className="text-center py-10 text-text-secondary">
              No clusters registered.{" "}
              <Button variant="link" onClick={() => setClusterOpen(true)} className="text-accent-brand font-semibold hover:underline p-0 h-auto">+ Add first cluster</Button>
            </div>
          ) : (
            <div className="flex flex-col gap-3">
              {clusters.map(c => (
                <Card key={c.id} className="rounded-2xl border-border-default bg-bg-elevated/50 p-4 sm:px-5">
                  <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                  <div className="min-w-0">
                    <div className="font-semibold text-sm">{c.display_name}</div>
                    <div title={c.api_endpoint} className="max-w-full truncate text-xs text-text-tertiary font-mono md:max-w-[420px]">{c.api_endpoint}</div>
                  </div>
                  <div className="flex items-center gap-3">
                    <Badge variant={c.onboarding_state === "ready" ? "default" : "secondary"}>{c.onboarding_state}</Badge>
                    <Button variant="ghost" size="icon" onClick={() => setDeleteTarget({ id: c.id, type: "cluster", label: c.display_name })}>
                      <Trash2 size={14} className="text-text-tertiary" />
                    </Button>
                  </div>
                  </div>
                </Card>
              ))}
            </div>
          )}
        </TabsContent>

        {/* Definitions */}
        <TabsContent value="definitions" className="mt-6 rounded-2xl border border-border-default bg-bg-surface p-5 shadow-card sm:p-6">
          <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <span className="text-sm font-semibold text-text-secondary">Definitions</span>
            <Dialog open={defOpen} onOpenChange={setDefOpen}>
              <DialogTrigger asChild><Button size="sm" className="shrink-0"><Plus size={14} /> Add</Button></DialogTrigger>
              <DialogContent className="max-w-lg">
                <DialogHeader><DialogTitle>Create Definition</DialogTitle></DialogHeader>
                <div className="flex flex-col gap-4">
                  <div className="space-y-2">
                    <Label>Kind</Label>
                    <Select value={defForm.kind} onValueChange={v => setDefForm(f => ({ ...f, kind: v }))}>
                      <SelectTrigger><SelectValue /></SelectTrigger>
                      <SelectContent>
                        <SelectItem value="scanner">Scanner</SelectItem>
                        <SelectItem value="tool">Tool</SelectItem>
                        <SelectItem value="skill">Skill</SelectItem>
                        <SelectItem value="pipeline">Pipeline</SelectItem>
                        <SelectItem value="policy">Policy</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-2"><Label>Name *</Label><Input value={defForm.name} onChange={e => setDefForm(f => ({ ...f, name: e.target.value }))} placeholder="my-scanner" /></div>
                  <div className="space-y-2"><Label>Version</Label><Input value={defForm.version} onChange={e => setDefForm(f => ({ ...f, version: e.target.value }))} placeholder="1" /></div>
                  <div className="space-y-2"><Label>Frontmatter (JSON)</Label><Textarea value={defForm.frontmatter} onChange={e => setDefForm(f => ({ ...f, frontmatter: e.target.value }))} className="font-mono text-xs" rows={4} /></div>
                  <div className="space-y-2"><Label>Body (Markdown)</Label><Textarea value={defForm.body} onChange={e => setDefForm(f => ({ ...f, body: e.target.value }))} rows={6} placeholder="# Content" /></div>
                </div>
                <DialogFooter>
                  <Button variant="outline" onClick={() => setDefOpen(false)}>Cancel</Button>
                  <Button onClick={createDefinition} disabled={!defForm.name}>Create</Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>
          </div>
          {definitions.length === 0 ? (
            <div className="text-center py-10 text-text-secondary">No definitions in DB. Built-in definitions are loaded from the filesystem.</div>
          ) : (
            <div className="flex flex-col gap-3">
              {definitions.map(d => (
                <Card key={d.id} className="rounded-2xl border-border-default bg-bg-elevated/50 p-4 sm:px-5">
                  <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                    <div className="flex min-w-0 items-center gap-3">
                    <Badge variant="outline" className="uppercase text-[11px]">{d.kind}</Badge>
                    <span className="font-semibold">{d.name}</span>
                    <span className="text-xs text-text-tertiary">v{d.version}</span>
                    </div>
                    <div className="flex items-center gap-3">
                      <span className={`text-xs ${d.enabled ? "text-status-done" : "text-text-tertiary"}`}>{d.enabled ? "Enabled" : "Disabled"}</span>
                      <Button variant="ghost" size="icon" onClick={() => setDeleteTarget({ id: `${d.kind}/${d.name}`, type: "definition", label: d.name })}>
                        <Trash2 size={14} className="text-text-tertiary" />
                      </Button>
                    </div>
                  </div>
                </Card>
              ))}
            </div>
          )}
        </TabsContent>

        {/* Webhooks */}
        <TabsContent value="webhooks" className="mt-6 rounded-2xl border border-border-default bg-bg-surface p-5 shadow-card sm:p-6">
          <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <span className="text-sm font-semibold text-text-secondary">Webhook Subscriptions</span>
            <Dialog open={webhookOpen} onOpenChange={setWebhookOpen}>
              <DialogTrigger asChild><Button size="sm" className="shrink-0"><Plus size={14} /> Add</Button></DialogTrigger>
              <DialogContent>
                <DialogHeader><DialogTitle>Create Webhook</DialogTitle></DialogHeader>
                <div className="flex flex-col gap-4">
                  <div className="space-y-2"><Label>Name *</Label><Input value={webhookForm.name} onChange={e => setWebhookForm(f => ({ ...f, name: e.target.value }))} placeholder="slack-alerts" /></div>
                  <div className="space-y-2"><Label>URL *</Label><Input value={webhookForm.url} onChange={e => setWebhookForm(f => ({ ...f, url: e.target.value }))} placeholder="https://hooks.slack.com/..." /></div>
                  <div className="space-y-2"><Label>Event Patterns</Label><Input value={webhookForm.event_patterns} onChange={e => setWebhookForm(f => ({ ...f, event_patterns: e.target.value }))} placeholder="work_item.*, issue.*" /><p className="text-[11px] text-text-tertiary">Comma-separated patterns</p></div>
                  <div className="space-y-2">
                    <Label>Formatter</Label>
                    <Select value={webhookForm.formatter} onValueChange={v => setWebhookForm(f => ({ ...f, formatter: v }))}>
                      <SelectTrigger><SelectValue /></SelectTrigger>
                      <SelectContent>
                        <SelectItem value="generic">Generic</SelectItem>
                        <SelectItem value="slack">Slack</SelectItem>
                        <SelectItem value="pagerduty">PagerDuty</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>
                <DialogFooter>
                  <Button variant="outline" onClick={() => setWebhookOpen(false)}>Cancel</Button>
                  <Button onClick={createWebhook} disabled={!webhookForm.name || !webhookForm.url}>Create</Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>
          </div>
          {webhooks.length === 0 ? (
            <div className="text-center py-10 text-text-secondary">No webhook subscriptions. Create one to receive notifications.</div>
          ) : (
            <div className="flex flex-col gap-3">
              {webhooks.map(w => (
                <Card key={w.id} className="rounded-2xl border-border-default bg-bg-elevated/50 p-4 sm:px-5">
                  <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                  <div className="min-w-0">
                    <div className="font-semibold text-sm">{w.name}</div>
                    <div title={w.url} className="max-w-full truncate text-xs text-text-tertiary font-mono md:max-w-[420px]">{w.url}</div>
                  </div>
                  <div className="flex items-center gap-3">
                    <Badge variant="outline" className="uppercase text-[11px]">{w.formatter}</Badge>
                    <Button variant="ghost" size="icon" onClick={() => setDeleteTarget({ id: w.id, type: "webhook", label: w.name })}>
                      <Trash2 size={14} className="text-text-tertiary" />
                    </Button>
                  </div>
                  </div>
                </Card>
              ))}
            </div>
          )}
        </TabsContent>

        {/* Policy Rules */}
        <TabsContent value="rules" className="mt-6 rounded-2xl border border-border-default bg-bg-surface p-5 shadow-card sm:p-6">
          <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <span className="text-sm font-semibold text-text-secondary">Policy Rules</span>
            <Dialog open={ruleOpen} onOpenChange={setRuleOpen}>
              <DialogTrigger asChild><Button size="sm" className="shrink-0"><Plus size={14} /> Add</Button></DialogTrigger>
              <DialogContent className="max-w-lg">
                <DialogHeader><DialogTitle>Create Policy Rule</DialogTitle></DialogHeader>
                <div className="flex flex-col gap-4">
                  <div className="space-y-2"><Label>Name *</Label><Input value={ruleForm.name} onChange={e => setRuleForm(f => ({ ...f, name: e.target.value }))} placeholder="auto-investigate-critical" /></div>
                  <div className="space-y-2"><Label>Description</Label><Input value={ruleForm.description} onChange={e => setRuleForm(f => ({ ...f, description: e.target.value }))} placeholder="Optional" /></div>
                  <div className="space-y-2"><Label>Priority</Label><Input type="number" value={ruleForm.priority} onChange={e => setRuleForm(f => ({ ...f, priority: e.target.value }))} /><p className="text-[11px] text-text-tertiary">Lower = higher priority</p></div>
                  <div className="space-y-2"><Label>Conditions (JSON)</Label><Textarea value={ruleForm.conditions} onChange={e => setRuleForm(f => ({ ...f, conditions: e.target.value }))} className="font-mono text-xs" rows={4} /></div>
                  <div className="space-y-2"><Label>Action (JSON)</Label><Textarea value={ruleForm.action} onChange={e => setRuleForm(f => ({ ...f, action: e.target.value }))} className="font-mono text-xs" rows={4} /></div>
                </div>
                <DialogFooter>
                  <Button variant="outline" onClick={() => setRuleOpen(false)}>Cancel</Button>
                  <Button onClick={createRule} disabled={!ruleForm.name}>Create</Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>
          </div>
          {rules.length === 0 ? (
            <div className="text-center py-10 text-text-secondary">No policy rules configured.</div>
          ) : (
            <div className="flex flex-col gap-3">
              {rules.map(r => (
                <Card key={r.id} className="rounded-2xl border-border-default bg-bg-elevated/50 p-4 sm:px-5">
                  <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                  <div className="flex items-center gap-3">
                    <span className="tabular text-xs text-text-tertiary font-semibold min-w-[30px]">#{r.priority}</span>
                    <span className="font-semibold">{r.name}</span>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className={`text-xs ${r.enabled ? "text-status-done" : "text-text-tertiary"}`}>{r.enabled ? "Active" : "Inactive"}</span>
                    <Button variant="ghost" size="icon" onClick={() => setDeleteTarget({ id: r.id, type: "rule", label: r.name })}>
                      <Trash2 size={14} className="text-text-tertiary" />
                    </Button>
                  </div>
                  </div>
                </Card>
              ))}
            </div>
          )}
        </TabsContent>

        {/* Cluster Access */}
        <TabsContent value="access" className="mt-6 rounded-2xl border border-border-default bg-bg-surface p-5 shadow-card sm:p-6">
          <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <span className="text-sm font-semibold text-text-secondary">Your Cluster Bindings</span>
          </div>
          {bindings.length === 0 ? (
            <div className="text-center py-10 text-text-secondary">No cluster bindings. Connect to a cluster to enable remediations.</div>
          ) : (
            <div className="flex flex-col gap-3">
              {bindings.map(b => {
                const statusColor: Record<string, string> = {
                  valid: "text-status-done", expiring: "text-status-in-progress",
                  expired: "text-status-blocked", missing: "text-text-tertiary", revoked: "text-text-tertiary",
                };
                const cluster = clusters.find(c => c.id === b.cluster_id);
                return (
                  <Card key={b.id} className="rounded-2xl border-border-default bg-bg-elevated/50 p-4 sm:px-5">
                    <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                    <div className="min-w-0">
                      <div className="font-semibold text-sm">{cluster?.display_name ?? b.cluster_id}</div>
                      <div className="text-xs text-text-tertiary">
                        {b.binding_method} · {b.cluster_username || "no username"} · expires {b.expires_at ? new Date(b.expires_at).toLocaleString() : "never"}
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      <span className={`text-xs font-semibold uppercase ${statusColor[b.status] || "text-text-tertiary"}`}>{b.status}</span>
                      {(b.status === "expired" || b.status === "expiring") && (
                        <Button variant="outline" size="sm" className="h-8 text-xs" onClick={async () => {
                          try { await api.post(`/api/v1/cluster-bindings/${b.id}/refresh`); toast.success("Binding refreshed"); refresh(); }
                          catch { toast.error("Failed to refresh"); }
                        }}>Refresh</Button>
                      )}
                      {b.status !== "revoked" && (
                        <Button variant="ghost" size="icon" onClick={() => setDeleteTarget({ id: b.id, type: "binding", label: cluster?.display_name ?? "binding" })}>
                          <Trash2 size={14} className="text-text-tertiary" />
                        </Button>
                      )}
                    </div>
                    </div>
                  </Card>
                );
              })}
            </div>
          )}
          <div className="mt-4">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
              <Select value={bindingClusterId} onValueChange={setBindingClusterId}>
                <SelectTrigger className="w-full sm:w-[280px]">
                  <SelectValue placeholder="Select a cluster to bind" />
                </SelectTrigger>
                <SelectContent>
                  {clusters.map(c => (
                    <SelectItem key={c.id} value={c.id}>{c.display_name}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Button
                variant="outline"
                size="sm"
                className="shrink-0"
                disabled={!bindingClusterId}
                onClick={async () => {
                  if (!bindingClusterId) { toast.error("Select a cluster first"); return; }
                  try {
                    await api.post("/api/v1/cluster-bindings", { cluster_id: bindingClusterId });
                    toast.success("Binding created");
                    setBindingClusterId("");
                    refresh();
                  } catch (e) { toast.error(e instanceof Error ? e.message : "Failed"); }
                }}
              >
                <Plus size={14} /> Connect to Cluster
              </Button>
            </div>
          </div>
        </TabsContent>

        {/* Analytics */}
        <TabsContent value="analytics" className="mt-6 rounded-2xl border border-border-default bg-bg-surface p-5 shadow-card sm:p-6">
          <div className="flex items-center gap-2 mb-4">
            <Brain size={16} className="text-accent-brain" />
            <span className="text-sm font-semibold">ROI Metrics</span>
          </div>
          {Object.keys(roi).length === 0 ? (
            <div className="text-center py-10 text-text-secondary">No analytics data yet.</div>
          ) : (
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
              {Object.entries(roi).map(([k, v]) => (
                <Card key={k} className="rounded-2xl border-border-default bg-bg-elevated/50 p-4">
                  <div className="tabular text-3xl font-bold leading-none">{String(v ?? "—")}</div>
                  <div className="text-xs text-text-tertiary mt-1 capitalize">{k.replace(/_/g, " ")}</div>
                </Card>
              ))}
            </div>
          )}
        </TabsContent>
      </Tabs>

      {/* Delete Confirmation */}
      <AlertDialog open={deleteTarget !== null} onOpenChange={open => { if (!open) setDeleteTarget(null); }}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete {deleteTarget?.type}?</AlertDialogTitle>
            <AlertDialogDescription>
              This will permanently remove &quot;{deleteTarget?.label}&quot;. This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={handleDelete} className="bg-status-blocked hover:bg-status-blocked/90">Delete</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
