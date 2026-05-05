"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import type { ClusterRegistryEntry, PaginatedResponse } from "@pinky/contracts";
import { api } from "@/lib/api";
import { QUERY_KEYS } from "@/lib/constants";
import { bindingsOptions, clustersOptions } from "../queries";
import { EmptyState } from "@/components/shared/empty-state";
import { RelativeTime } from "@/components/shared/relative-time";
import { StatusDot } from "@/components/shared/status-indicator";
import { FadeIn } from "@/components/motion/fade-in";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Plus, Users, RefreshCw } from "lucide-react";
import { DeleteButton } from "./delete-button";
import { toast } from "sonner";

export function AccessTab() {
  const qc = useQueryClient();
  const { data } = useQuery(bindingsOptions());
  const { data: clusters } = useQuery(clustersOptions());
  const [connectOpen, setConnectOpen] = useState(false);

  const refresh = useMutation({
    mutationFn: (id: string) => api.post(`/api/v1/cluster-bindings/${id}/refresh`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: QUERY_KEYS.bindings() });
      toast.success("Binding refreshed");
    },
  });

  const revoke = useMutation({
    mutationFn: (id: string) => api.del(`/api/v1/cluster-bindings/${id}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: QUERY_KEYS.bindings() });
      toast.success("Binding revoked");
    },
  });

  const clusterMap: Record<string, string> = {};
  for (const c of clusters?.items ?? []) clusterMap[c.id] = c.display_name;

  return (
    <FadeIn>
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle className="text-sm">Cluster Bindings</CardTitle>
          <ConnectClusterDialog
            open={connectOpen}
            onOpenChange={setConnectOpen}
            clusters={clusters?.items ?? []}
          />
        </CardHeader>
        <CardContent>
          {(data?.items ?? []).length === 0 ? (
            <EmptyState icon={Users} title="No bindings" description="Connect to a cluster to create an identity binding" />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Cluster</TableHead>
                  <TableHead>Method</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Expires</TableHead>
                  <TableHead className="w-24" />
                </TableRow>
              </TableHeader>
              <TableBody>
                {(data?.items ?? []).map((b) => (
                  <TableRow key={b.id}>
                    <TableCell className="font-medium">{clusterMap[b.cluster_id] ?? b.cluster_id.slice(0, 8)}</TableCell>
                    <TableCell className="text-body-sm text-text-secondary">{b.binding_method}</TableCell>
                    <TableCell>
                      <span className="inline-flex items-center gap-1.5">
                        <StatusDot status={b.status === "valid" ? "done" : "blocked"} />
                        {b.status}
                      </span>
                    </TableCell>
                    <TableCell>{b.expires_at ? <RelativeTime date={b.expires_at} /> : "—"}</TableCell>
                    <TableCell>
                      <div className="flex items-center gap-1">
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-7 w-7 text-text-tertiary hover:text-text-secondary"
                          onClick={() => refresh.mutate(b.id)}
                          disabled={refresh.isPending}
                          title="Refresh credentials"
                        >
                          <RefreshCw size={14} />
                        </Button>
                        <DeleteButton onConfirm={() => revoke.mutate(b.id)} label={clusterMap[b.cluster_id] ?? "binding"} />
                      </div>
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

function ConnectClusterDialog({
  open,
  onOpenChange,
  clusters,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  clusters: ClusterRegistryEntry[];
}) {
  const qc = useQueryClient();
  const [clusterId, setClusterId] = useState("");

  const connect = useMutation({
    mutationFn: () =>
      api.post("/api/v1/cluster-bindings", {
        cluster_id: clusterId,
        binding_method: "oauth_login",
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: QUERY_KEYS.bindings() });
      setClusterId("");
      onOpenChange(false);
      toast.success("Cluster connected");
    },
    onError: () => toast.error("Failed to connect"),
  });

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogTrigger asChild>
        <Button size="sm" className="gap-1"><Plus size={14} />Connect</Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader><DialogTitle>Connect to Cluster</DialogTitle></DialogHeader>
        <div className="space-y-3">
          <Select value={clusterId} onValueChange={setClusterId}>
            <SelectTrigger><SelectValue placeholder="Select cluster" /></SelectTrigger>
            <SelectContent>
              {clusters.map((c) => (
                <SelectItem key={c.id} value={c.id}>{c.display_name}</SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Button onClick={() => connect.mutate()} disabled={!clusterId || connect.isPending} className="w-full">
            Connect
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
