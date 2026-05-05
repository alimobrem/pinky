"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { QUERY_KEYS } from "@/lib/constants";
import { clustersOptions } from "../queries";
import { EmptyState } from "@/components/shared/empty-state";
import { RelativeTime } from "@/components/shared/relative-time";
import { StatusDot } from "@/components/shared/status-indicator";
import { FadeIn } from "@/components/motion/fade-in";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Plus, Server } from "lucide-react";
import { DeleteButton } from "./delete-button";
import { toast } from "sonner";

export function ClustersTab() {
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
                <TableRow><TableHead>Name</TableHead><TableHead>State</TableHead><TableHead>Created</TableHead><TableHead className="w-12" /></TableRow>
              </TableHeader>
              <TableBody>
                {clusters.map((c) => (
                  <TableRow key={c.id}>
                    <TableCell className="font-medium">{c.display_name}</TableCell>
                    <TableCell><StatusDot status={c.onboarding_state === "ready" ? "done" : "blocked"} /> {c.onboarding_state}</TableCell>
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
