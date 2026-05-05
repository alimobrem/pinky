"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { QUERY_KEYS } from "@/lib/constants";
import { definitionsOptions } from "../queries";
import { EmptyState } from "@/components/shared/empty-state";
import { FadeIn } from "@/components/motion/fade-in";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Plus, FileText, Eye } from "lucide-react";
import { DeleteButton } from "./delete-button";
import { toast } from "sonner";
import type { Definition } from "@pinky/contracts";

const DEFINITION_KINDS = ["scanner", "tool", "skill", "pipeline", "policy", "redaction"];

export function DefinitionsTab() {
  const qc = useQueryClient();
  const { data } = useQuery(definitionsOptions());
  const [kindFilter, setKindFilter] = useState<string>("all");
  const [createOpen, setCreateOpen] = useState(false);
  const [viewDef, setViewDef] = useState<Definition | null>(null);

  const items = (data?.items ?? []).filter(
    (d) => kindFilter === "all" || d.kind === kindFilter,
  );
  const kinds = [...new Set((data?.items ?? []).map((d) => d.kind))];

  const del = useMutation({
    mutationFn: (d: { kind: string; name: string }) =>
      api.del(`/api/v1/definitions/${d.kind}/${d.name}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: QUERY_KEYS.definitions() });
      toast.success("Definition deleted");
    },
  });

  return (
    <FadeIn>
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle className="text-sm">Definitions</CardTitle>
          <div className="flex items-center gap-2">
            <div className="flex gap-1">
              {["all", ...kinds].map((k) => (
                <Button
                  key={k}
                  size="sm"
                  variant={kindFilter === k ? "default" : "ghost"}
                  className="h-6 px-2 text-caption"
                  onClick={() => setKindFilter(k)}
                >
                  {k}
                </Button>
              ))}
            </div>
            <CreateDefinitionDialog open={createOpen} onOpenChange={setCreateOpen} />
          </div>
        </CardHeader>
        <CardContent>
          {items.length === 0 ? (
            <EmptyState icon={FileText} title="No definitions" description="Create scanners, tools, skills, and pipelines" />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>Kind</TableHead>
                  <TableHead>Version</TableHead>
                  <TableHead>Enabled</TableHead>
                  <TableHead className="w-20" />
                </TableRow>
              </TableHeader>
              <TableBody>
                {items.map((d) => (
                  <TableRow key={d.id}>
                    <TableCell className="font-medium">{d.name}</TableCell>
                    <TableCell>
                      <span className="rounded bg-bg-hover px-1.5 py-0.5 font-mono text-caption">{d.kind}</span>
                    </TableCell>
                    <TableCell className="font-mono text-xs text-text-tertiary">{d.version}</TableCell>
                    <TableCell><Switch checked={d.enabled} disabled /></TableCell>
                    <TableCell>
                      <div className="flex items-center gap-1">
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-7 w-7 text-text-tertiary hover:text-text-secondary"
                          onClick={() => setViewDef(d)}
                        >
                          <Eye size={14} />
                        </Button>
                        <DeleteButton
                          onConfirm={() => del.mutate({ kind: d.kind, name: d.name })}
                          label={d.name}
                        />
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      <Dialog open={!!viewDef} onOpenChange={(open) => !open && setViewDef(null)}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <span className="rounded bg-bg-hover px-1.5 py-0.5 font-mono text-caption">{viewDef?.kind}</span>
              {viewDef?.name}
            </DialogTitle>
          </DialogHeader>
          {viewDef && (
            <div className="space-y-4">
              <div className="flex items-center gap-4 text-sm text-text-secondary">
                <span>Version: <span className="font-mono">{viewDef.version}</span></span>
                <span>Enabled: {viewDef.enabled ? "Yes" : "No"}</span>
              </div>
              {Object.keys(viewDef.frontmatter).length > 0 && (
                <div>
                  <Label className="text-caption font-semibold uppercase tracking-widest text-text-tertiary">Frontmatter</Label>
                  <pre className="mt-1 max-h-48 overflow-auto rounded-lg bg-bg-hover p-3 font-mono text-xs text-text-secondary">
                    {JSON.stringify(viewDef.frontmatter, null, 2)}
                  </pre>
                </div>
              )}
              <div>
                <Label className="text-caption font-semibold uppercase tracking-widest text-text-tertiary">Body</Label>
                <pre className="mt-1 max-h-64 overflow-auto whitespace-pre-wrap rounded-lg bg-bg-hover p-3 font-mono text-xs text-text-secondary">
                  {viewDef.body || "(empty)"}
                </pre>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </FadeIn>
  );
}

function CreateDefinitionDialog({ open, onOpenChange }: { open: boolean; onOpenChange: (open: boolean) => void }) {
  const qc = useQueryClient();
  const [kind, setKind] = useState("scanner");
  const [name, setName] = useState("");
  const [version, setVersion] = useState("1.0.0");
  const [enabled, setEnabled] = useState(true);
  const [frontmatter, setFrontmatter] = useState("{}");
  const [body, setBody] = useState("");

  const create = useMutation({
    mutationFn: () =>
      api.post("/api/v1/definitions", {
        kind,
        name,
        version,
        enabled,
        frontmatter: JSON.parse(frontmatter),
        body,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: QUERY_KEYS.definitions() });
      setName(""); setBody(""); setFrontmatter("{}");
      onOpenChange(false);
      toast.success("Definition created");
    },
    onError: () => toast.error("Failed to create definition"),
  });

  const valid = name.length > 0 && (() => { try { JSON.parse(frontmatter); return true; } catch { return false; } })();

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogTrigger asChild>
        <Button size="sm" className="gap-1"><Plus size={14} />Create</Button>
      </DialogTrigger>
      <DialogContent className="max-w-lg">
        <DialogHeader><DialogTitle>Create Definition</DialogTitle></DialogHeader>
        <div className="space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label className="text-xs text-text-secondary">Kind</Label>
              <Select value={kind} onValueChange={setKind}>
                <SelectTrigger className="mt-1"><SelectValue /></SelectTrigger>
                <SelectContent>
                  {DEFINITION_KINDS.map((k) => (
                    <SelectItem key={k} value={k}>{k}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label className="text-xs text-text-secondary">Name</Label>
              <Input className="mt-1" value={name} onChange={(e) => setName(e.target.value)} placeholder="my-scanner" />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label className="text-xs text-text-secondary">Version</Label>
              <Input className="mt-1" value={version} onChange={(e) => setVersion(e.target.value)} />
            </div>
            <div className="flex items-end gap-2 pb-1">
              <Switch checked={enabled} onCheckedChange={setEnabled} />
              <Label className="text-sm">Enabled</Label>
            </div>
          </div>
          <div>
            <Label className="text-xs text-text-secondary">Frontmatter (JSON)</Label>
            <Textarea className="mt-1 font-mono text-xs" rows={3} value={frontmatter} onChange={(e) => setFrontmatter(e.target.value)} />
          </div>
          <div>
            <Label className="text-xs text-text-secondary">Body (Markdown)</Label>
            <Textarea className="mt-1 font-mono text-xs" rows={6} value={body} onChange={(e) => setBody(e.target.value)} placeholder="# Scanner logic..." />
          </div>
          <Button onClick={() => create.mutate()} disabled={!valid || create.isPending} className="w-full">
            Create Definition
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
