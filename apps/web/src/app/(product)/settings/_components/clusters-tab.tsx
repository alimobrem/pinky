"use client";

import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useRetryableMutation } from "@/hooks/use-retryable-mutation";
import { api, ApiError } from "@/lib/api";
import { QUERY_KEYS } from "@/lib/constants";
import { clustersOptions, observerBindingOptions } from "../queries";
import { EmptyState } from "@/components/shared/empty-state";
import { RelativeTime } from "@/components/shared/relative-time";
import { StatusDot } from "@/components/shared/status-indicator";
import { FadeIn } from "@/components/motion/fade-in";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import Link from "next/link";
import { Eye, Loader2, Plus, Server } from "lucide-react";
import { DeleteButton } from "./delete-button";
import { toast } from "sonner";
import type { ClusterRegistryEntry } from "@pinky/contracts";

export function ClustersTab() {
  const qc = useQueryClient();
  const { data } = useQuery(clustersOptions());
  const [name, setName] = useState("");
  const [endpoint, setEndpoint] = useState("");

  const create = useRetryableMutation({
    errorMessage: "Failed to create cluster",
    mutationFn: () =>
      api.post("/api/v1/clusters", { display_name: name, api_endpoint: endpoint }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: QUERY_KEYS.clusters() });
      setName(""); setEndpoint("");
      toast.success("Cluster created");
    },
  });

  const del = useRetryableMutation({
    errorMessage: "Failed to delete cluster",
    mutationFn: (id: string) => api.del(`/api/v1/clusters/${id}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: QUERY_KEYS.clusters() });
      toast.success("Cluster deleted");
    },
  });

  const clusters = data?.items ?? [];

  return (
    <FadeIn>
      <Card>
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
                <Button onClick={() => create.mutate()} disabled={!name || !endpoint || create.isPending}>Create</Button>
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
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>State</TableHead>
                  <TableHead>Observer</TableHead>
                  <TableHead>Created</TableHead>
                  <TableHead className="w-12" />
                </TableRow>
              </TableHeader>
              <TableBody>
                {clusters.map((c) => (
                  <TableRow key={c.id}>
                    <TableCell className="font-medium">
                      <Link href={`/clusters/${c.id}`} className="hover:underline">
                        {c.display_name}
                      </Link>
                    </TableCell>
                    <TableCell><StatusDot status={c.onboarding_state === "ready" ? "done" : "blocked"} /> {c.onboarding_state}</TableCell>
                    <TableCell>
                      <ObserverBindingCell cluster={c} />
                    </TableCell>
                    <TableCell><RelativeTime date={c.created_at} /></TableCell>
                    <TableCell><DeleteButton onConfirm={() => del.mutate(c.id)} label={c.display_name} /></TableCell>
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

/* ------------------------------------------------------------------ */
/*  Observer binding — per-row cell + dialog                          */
/* ------------------------------------------------------------------ */

function ObserverBindingCell({ cluster }: { cluster: ClusterRegistryEntry }) {
  const [open, setOpen] = useState(false);

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="ghost" size="sm" className="gap-1.5 text-xs">
          <Eye size={13} />
          Configure
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Configure Observer</DialogTitle>
          <DialogDescription>{cluster.display_name}</DialogDescription>
        </DialogHeader>
        {open && (
          <ObserverBindingForm clusterId={cluster.id} onClose={() => setOpen(false)} />
        )}
      </DialogContent>
    </Dialog>
  );
}

function ObserverBindingForm({
  clusterId,
  onClose,
}: {
  clusterId: string;
  onClose: () => void;
}) {
  const qc = useQueryClient();
  const [token, setToken] = useState("");

  const { data: binding, isLoading, isError } = useQuery(
    observerBindingOptions(clusterId, true),
  );

  const save = useRetryableMutation({
    errorMessage: "Failed to save observer binding",
    mutationFn: () =>
      api.post(`/api/v1/clusters/${clusterId}/observer-binding`, { token }),
    onSuccess: () => {
      setToken("");
      qc.invalidateQueries({ queryKey: QUERY_KEYS.observerBinding(clusterId) });
      qc.invalidateQueries({ queryKey: QUERY_KEYS.clusters() });
      toast.success("Observer binding saved");
      onClose();
    },
  });

  const remove = useRetryableMutation({
    errorMessage: "Failed to remove observer binding",
    mutationFn: () => api.del(`/api/v1/clusters/${clusterId}/observer-binding`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: QUERY_KEYS.observerBinding(clusterId) });
      qc.invalidateQueries({ queryKey: QUERY_KEYS.clusters() });
      toast.success("Observer binding removed");
      onClose();
    },
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-6">
        <Loader2 size={16} className="animate-spin text-text-tertiary" />
      </div>
    );
  }

  if (isError) {
    return (
      <p className="text-sm text-destructive">Failed to load observer binding status.</p>
    );
  }

  // Binding exists — show status + remove
  if (binding) {
    return (
      <div className="space-y-4">
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <span className="text-sm text-text-secondary">Health</span>
            <ObserverHealthDot health={binding.health_state} />
            <Badge variant="outline" className="text-xs">{binding.health_state}</Badge>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-sm text-text-secondary">Auth method</span>
            <span className="text-sm">{binding.auth_method}</span>
          </div>
          {binding.last_observation_at && (
            <div className="flex items-center gap-2">
              <span className="text-sm text-text-secondary">Last observation</span>
              <RelativeTime date={binding.last_observation_at} />
            </div>
          )}
          <div className="flex items-center gap-2">
            <span className="text-sm text-text-secondary">Created</span>
            <RelativeTime date={binding.created_at} />
          </div>
        </div>
        <Button
          variant="destructive"
          size="sm"
          onClick={() => remove.mutate()}
          disabled={remove.isPending}
        >
          {remove.isPending ? "Removing…" : "Remove binding"}
        </Button>
      </div>
    );
  }

  // No binding — show token form
  return (
    <div className="space-y-4">
      <p className="text-sm text-text-secondary">
        Create a ServiceAccount with cluster-reader ClusterRole on the target
        cluster, then paste the token here.
      </p>
      <Input
        type="password"
        value={token}
        onChange={(e) => setToken(e.target.value)}
        placeholder="ServiceAccount token"
        autoComplete="off"
      />
      <Button
        onClick={() => save.mutate()}
        disabled={!token.trim() || save.isPending}
      >
        {save.isPending ? "Saving…" : "Save"}
      </Button>
    </div>
  );
}

function ObserverHealthDot({ health }: { health: string }) {
  let color = "bg-border";
  if (health === "healthy") color = "bg-emerald-500";
  else if (health === "unknown" || health === "degraded") color = "bg-amber-500";
  else if (health === "unhealthy") color = "bg-destructive";

  return (
    <span
      className={`inline-block size-2 rounded-full ${color}`}
      title={health}
    />
  );
}
