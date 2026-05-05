"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { QUERY_KEYS } from "@/lib/constants";
import {
  clustersOptions,
  definitionsOptions,
  webhooksOptions,
  policyRulesOptions,
  bindingsOptions,
  analyticsRoiOptions,
  analyticsScannersOptions,
} from "../queries";
import { PageHeader } from "@/components/shared/page-header";
import { EmptyState } from "@/components/shared/empty-state";
import { RelativeTime } from "@/components/shared/relative-time";
import { StatusDot } from "@/components/shared/status-indicator";
import { FadeIn } from "@/components/motion/fade-in";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { Plus, Trash2, Server, FileText, Webhook, Shield, Users, BarChart3 } from "lucide-react";
import type { Definition } from "@pinky/contracts";
import { toast } from "sonner";

export function SettingsView() {
  return (
    <div className="space-y-4">
      <PageHeader title="Settings" description="Platform configuration" />

      <Tabs defaultValue="clusters">
        <TabsList className="border-b border-border-subtle bg-transparent">
          <TabsTrigger value="clusters" className="gap-1.5"><Server size={14} />Clusters</TabsTrigger>
          <TabsTrigger value="definitions" className="gap-1.5"><FileText size={14} />Definitions</TabsTrigger>
          <TabsTrigger value="webhooks" className="gap-1.5"><Webhook size={14} />Webhooks</TabsTrigger>
          <TabsTrigger value="rules" className="gap-1.5"><Shield size={14} />Rules</TabsTrigger>
          <TabsTrigger value="access" className="gap-1.5"><Users size={14} />Access</TabsTrigger>
          <TabsTrigger value="analytics" className="gap-1.5"><BarChart3 size={14} />Analytics</TabsTrigger>
        </TabsList>

        <TabsContent value="clusters"><ClustersTab /></TabsContent>
        <TabsContent value="definitions"><DefinitionsTab /></TabsContent>
        <TabsContent value="webhooks"><WebhooksTab /></TabsContent>
        <TabsContent value="rules"><RulesTab /></TabsContent>
        <TabsContent value="access"><AccessTab /></TabsContent>
        <TabsContent value="analytics"><AnalyticsTab /></TabsContent>
      </Tabs>
    </div>
  );
}

function ClustersTab() {
  const qc = useQueryClient();
  const { data } = useQuery(clustersOptions());
  const [name, setName] = useState("");
  const [endpoint, setEndpoint] = useState("");

  const create = useMutation({
    mutationFn: () =>
      api.post("/api/v1/clusters", { display_name: name, api_endpoint: endpoint }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: QUERY_KEYS.clusters() });
      setName(""); setEndpoint("");
      toast.success("Cluster created");
    },
  });

  const del = useMutation({
    mutationFn: (id: string) => api.del(`/api/v1/clusters/${id}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: QUERY_KEYS.clusters() });
      toast.success("Cluster deleted");
    },
  });

  const clusters = data?.items ?? [];

  return (
    <FadeIn>
      <Card className="border-border-subtle bg-bg-surface">
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle className="text-sm">Clusters</CardTitle>
          <Dialog>
            <DialogTrigger asChild>
              <Button size="sm" className="gap-1"><Plus size={14} />Add</Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader><DialogTitle>Add cluster</DialogTitle></DialogHeader>
              <div className="space-y-3">
                <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="Display name" />
                <Input value={endpoint} onChange={(e) => setEndpoint(e.target.value)} placeholder="API endpoint" />
                <Button onClick={() => create.mutate()} disabled={!name || !endpoint || create.isPending}>
                  Create
                </Button>
              </div>
            </DialogContent>
          </Dialog>
        </CardHeader>
        <CardContent>
          {clusters.length === 0 ? (
            <EmptyState icon={Server} title="No clusters" description="Add a cluster to get started" />
          ) : (
            <Table>
              <TableHeader>
                <TableRow><TableHead>Name</TableHead><TableHead>State</TableHead><TableHead>Created</TableHead><TableHead className="w-12" /></TableRow>
              </TableHeader>
              <TableBody>
                {clusters.map((c) => (
                  <TableRow key={c.id}>
                    <TableCell className="font-medium">{c.display_name}</TableCell>
                    <TableCell><StatusDot status={c.onboarding_state === "ready" ? "done" : "blocked"} /> {c.onboarding_state}</TableCell>
                    <TableCell><RelativeTime date={c.created_at} /></TableCell>
                    <TableCell>
                      <DeleteButton onConfirm={() => del.mutate(c.id)} label={c.display_name} />
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </FadeIn>
  );
}

function DefinitionsTab() {
  const { data } = useQuery(definitionsOptions());
  const [kindFilter, setKindFilter] = useState<string>("all");
  const items = (data?.items ?? []).filter(
    (d) => kindFilter === "all" || d.kind === kindFilter,
  );
  const kinds = [...new Set((data?.items ?? []).map((d) => d.kind))];

  return (
    <FadeIn>
      <Card className="border-border-subtle bg-bg-surface">
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle className="text-sm">Definitions</CardTitle>
          <div className="flex gap-1">
            {["all", ...kinds].map((k) => (
              <Button
                key={k}
                size="sm"
                variant={kindFilter === k ? "default" : "ghost"}
                className="h-6 px-2 text-[11px]"
                onClick={() => setKindFilter(k)}
              >
                {k}
              </Button>
            ))}
          </div>
        </CardHeader>
        <CardContent>
          {items.length === 0 ? (
            <EmptyState icon={FileText} title="No definitions" description="Definitions are loaded from the definitions/ directory" />
          ) : (
            <Table>
              <TableHeader>
                <TableRow><TableHead>Name</TableHead><TableHead>Kind</TableHead><TableHead>Version</TableHead><TableHead>Enabled</TableHead></TableRow>
              </TableHeader>
              <TableBody>
                {items.map((d) => (
                  <TableRow key={d.id}>
                    <TableCell className="font-medium">{d.name}</TableCell>
                    <TableCell><span className="rounded bg-bg-hover px-1.5 py-0.5 font-mono text-[11px]">{d.kind}</span></TableCell>
                    <TableCell className="font-mono text-xs text-text-tertiary">{d.version}</TableCell>
                    <TableCell><Switch checked={d.enabled} disabled /></TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </FadeIn>
  );
}

function WebhooksTab() {
  const qc = useQueryClient();
  const { data } = useQuery(webhooksOptions());

  const del = useMutation({
    mutationFn: (id: string) => api.del(`/api/v1/webhook-subscriptions/${id}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: QUERY_KEYS.webhooks() });
      toast.success("Webhook deleted");
    },
  });

  return (
    <FadeIn>
      <Card className="border-border-subtle bg-bg-surface">
        <CardHeader><CardTitle className="text-sm">Webhooks</CardTitle></CardHeader>
        <CardContent>
          {(data?.items ?? []).length === 0 ? (
            <EmptyState icon={Webhook} title="No webhooks" description="Configure webhook subscriptions for event notifications" />
          ) : (
            <Table>
              <TableHeader>
                <TableRow><TableHead>Name</TableHead><TableHead>URL</TableHead><TableHead>Enabled</TableHead><TableHead className="w-12" /></TableRow>
              </TableHeader>
              <TableBody>
                {(data?.items ?? []).map((w) => (
                  <TableRow key={w.id}>
                    <TableCell className="font-medium">{w.name}</TableCell>
                    <TableCell className="font-mono text-xs text-text-tertiary truncate max-w-[200px]">{w.url}</TableCell>
                    <TableCell><Switch checked={w.enabled} disabled /></TableCell>
                    <TableCell><DeleteButton onConfirm={() => del.mutate(w.id)} label={w.name} /></TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </FadeIn>
  );
}

function RulesTab() {
  const qc = useQueryClient();
  const { data } = useQuery(policyRulesOptions());

  const del = useMutation({
    mutationFn: (id: string) => api.del(`/api/v1/policy-rules/${id}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: QUERY_KEYS.policyRules() });
      toast.success("Rule deleted");
    },
  });

  return (
    <FadeIn>
      <Card className="border-border-subtle bg-bg-surface">
        <CardHeader><CardTitle className="text-sm">Policy Rules</CardTitle></CardHeader>
        <CardContent>
          {(data?.items ?? []).length === 0 ? (
            <EmptyState icon={Shield} title="No rules" description="Policy rules control how the Brain responds to signals" />
          ) : (
            <Table>
              <TableHeader>
                <TableRow><TableHead>Name</TableHead><TableHead>Priority</TableHead><TableHead>Enabled</TableHead><TableHead className="w-12" /></TableRow>
              </TableHeader>
              <TableBody>
                {(data?.items ?? []).map((r) => (
                  <TableRow key={r.id}>
                    <TableCell className="font-medium">{r.name}</TableCell>
                    <TableCell className="font-mono text-xs">{r.priority}</TableCell>
                    <TableCell><Switch checked={r.enabled} disabled /></TableCell>
                    <TableCell><DeleteButton onConfirm={() => del.mutate(r.id)} label={r.name} /></TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </FadeIn>
  );
}

function AccessTab() {
  const { data } = useQuery(bindingsOptions());
  return (
    <FadeIn>
      <Card className="border-border-subtle bg-bg-surface">
        <CardHeader><CardTitle className="text-sm">Cluster Bindings</CardTitle></CardHeader>
        <CardContent>
          {(data?.items ?? []).length === 0 ? (
            <EmptyState icon={Users} title="No bindings" description="Cluster identity bindings will appear here after login" />
          ) : (
            <Table>
              <TableHeader>
                <TableRow><TableHead>Cluster</TableHead><TableHead>Method</TableHead><TableHead>Status</TableHead><TableHead>Expires</TableHead></TableRow>
              </TableHeader>
              <TableBody>
                {(data?.items ?? []).map((b) => (
                  <TableRow key={b.id}>
                    <TableCell className="font-mono text-xs">{b.cluster_id.slice(0, 8)}</TableCell>
                    <TableCell>{b.binding_method}</TableCell>
                    <TableCell><StatusDot status={b.status === "valid" ? "done" : "blocked"} /> {b.status}</TableCell>
                    <TableCell>{b.expires_at ? <RelativeTime date={b.expires_at} /> : "—"}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </FadeIn>
  );
}

function AnalyticsTab() {
  const { data: roi } = useQuery(analyticsRoiOptions());
  const { data: scanners } = useQuery(analyticsScannersOptions());
  const m = roi?.metrics;

  return (
    <FadeIn>
      <div className="space-y-4">
        <div className="grid gap-4 sm:grid-cols-3">
          <MetricCard label="Issues Resolved" value={m?.issues_resolved ?? 0} total={m?.issues_total ?? 0} />
          <MetricCard label="Tasks Completed" value={m?.tasks_completed ?? 0} total={m?.tasks_total ?? 0} />
          <MetricCard label="Completion Rate" value={m ? Math.round(m.task_completion_rate * 100) : 0} suffix="%" />
        </div>

        <Card className="border-border-subtle bg-bg-surface">
          <CardHeader><CardTitle className="text-sm">Scanner Activity</CardTitle></CardHeader>
          <CardContent>
            {!scanners?.scanners?.length ? (
              <EmptyState icon={BarChart3} title="No data" description="Scanner metrics will appear after first scan" />
            ) : (
              <Table>
                <TableHeader>
                  <TableRow><TableHead>Scanner</TableHead><TableHead className="text-right">Signals</TableHead></TableRow>
                </TableHeader>
                <TableBody>
                  {scanners.scanners.map((s) => (
                    <TableRow key={s.scanner}>
                      <TableCell className="font-mono text-xs">{s.scanner}</TableCell>
                      <TableCell className="text-right font-mono tabular">{s.signal_total}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>
      </div>
    </FadeIn>
  );
}

function MetricCard({ label, value, total, suffix }: { label: string; value: number; total?: number; suffix?: string }) {
  return (
    <Card className="border-border-subtle bg-bg-surface">
      <CardContent className="p-4">
        <p className="text-[12px] text-text-tertiary">{label}</p>
        <p className="mt-1 font-mono text-2xl font-bold tabular text-text-primary">
          {value}{suffix}
          {total != null && <span className="text-sm font-normal text-text-tertiary"> / {total}</span>}
        </p>
      </CardContent>
    </Card>
  );
}

function DeleteButton({ onConfirm, label }: { onConfirm: () => void; label: string }) {
  return (
    <AlertDialog>
      <AlertDialogTrigger asChild>
        <Button variant="ghost" size="icon" className="h-7 w-7 text-text-tertiary hover:text-status-blocked">
          <Trash2 size={14} />
        </Button>
      </AlertDialogTrigger>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Delete &ldquo;{label}&rdquo;?</AlertDialogTitle>
          <AlertDialogDescription>This action cannot be undone.</AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel>Cancel</AlertDialogCancel>
          <AlertDialogAction className="bg-destructive text-destructive-foreground" onClick={onConfirm}>Delete</AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
