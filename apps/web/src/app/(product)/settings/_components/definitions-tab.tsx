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
import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Plus, FileText, Pencil, Eye, Save, Database, HardDrive } from "lucide-react";
import { DeleteButton } from "./delete-button";
import { toast } from "sonner";
import type { Definition } from "@pinky/contracts";

const DEFINITION_KINDS = ["scanner", "tool", "skill", "pipeline", "policy", "redaction-rule"];

export function DefinitionsTab() {
  const qc = useQueryClient();
  const { data } = useQuery(definitionsOptions());
  const [kindFilter, setKindFilter] = useState<string>("all");
  const [createOpen, setCreateOpen] = useState(false);
  const [editDef, setEditDef] = useState<Definition | null>(null);

  const items = (data?.items ?? []).filter(
    (d) => kindFilter === "all" || d.kind === kindFilter,
  );
  const kinds = [...new Set((data?.items ?? []).map((d) => d.kind))].sort();

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
          <CardTitle className="text-sm">
            Definitions
            <span className="ml-2 text-xs font-normal text-text-tertiary">({items.length})</span>
          </CardTitle>
          <div className="flex items-center gap-2">
            <div className="flex flex-wrap gap-1">
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
                  <TableHead>Source</TableHead>
                  <TableHead>Enabled</TableHead>
                  <TableHead className="w-24" />
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
                    <TableCell>
                      <SourceBadge source={(d as Definition & { source?: string }).source} />
                    </TableCell>
                    <TableCell><Switch checked={d.enabled} disabled /></TableCell>
                    <TableCell>
                      <div className="flex items-center gap-1">
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-7 w-7 text-text-tertiary hover:text-text-secondary"
                          onClick={() => setEditDef(d)}
                          title="View / Edit"
                        >
                          <Pencil size={14} />
                        </Button>
                        {(d as Definition & { source?: string }).source !== "filesystem" && (
                          <DeleteButton
                            onConfirm={() => del.mutate({ kind: d.kind, name: d.name })}
                            label={d.name}
                          />
                        )}
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {editDef && (
        <EditDefinitionDialog
          definition={editDef}
          onClose={() => setEditDef(null)}
        />
      )}
    </FadeIn>
  );
}

function SourceBadge({ source }: { source?: string }) {
  if (source === "filesystem") {
    return (
      <Badge variant="outline" className="gap-1 text-xs font-normal">
        <HardDrive size={10} />
        built-in
      </Badge>
    );
  }
  return (
    <Badge variant="secondary" className="gap-1 text-xs font-normal">
      <Database size={10} />
      custom
    </Badge>
  );
}

function EditDefinitionDialog({
  definition,
  onClose,
}: {
  definition: Definition;
  onClose: () => void;
}) {
  const qc = useQueryClient();
  const isFilesystem = (definition as Definition & { source?: string }).source === "filesystem";
  const [editing, setEditing] = useState(false);
  const [frontmatter, setFrontmatter] = useState(JSON.stringify(definition.frontmatter, null, 2));
  const [body, setBody] = useState(definition.body || "");
  const [enabled, setEnabled] = useState(definition.enabled);

  const save = useMutation({
    mutationFn: () =>
      api.post("/api/v1/definitions", {
        kind: definition.kind,
        name: definition.name,
        version: definition.version,
        enabled,
        frontmatter: JSON.parse(frontmatter),
        body,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: QUERY_KEYS.definitions() });
      setEditing(false);
      onClose();
      toast.success(isFilesystem ? "Override saved (DB overrides built-in)" : "Definition updated");
    },
    onError: () => toast.error("Failed to save definition"),
  });

  const validJson = (() => {
    try { JSON.parse(frontmatter); return true; } catch { return false; }
  })();

  return (
    <Dialog open onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-3xl max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <span className="rounded bg-bg-hover px-1.5 py-0.5 font-mono text-caption">{definition.kind}</span>
            {definition.name}
            <SourceBadge source={(definition as Definition & { source?: string }).source} />
          </DialogTitle>
        </DialogHeader>

        <div className="space-y-4">
          <div className="flex items-center gap-4 text-sm text-text-secondary">
            <span>Version: <span className="font-mono">{definition.version}</span></span>
            <div className="flex items-center gap-2">
              <span>Enabled:</span>
              <Switch checked={enabled} onCheckedChange={setEnabled} disabled={!editing} />
            </div>
            {!editing && (
              <Button size="sm" variant="outline" className="ml-auto gap-1" onClick={() => setEditing(true)}>
                <Pencil size={12} />
                {isFilesystem ? "Override" : "Edit"}
              </Button>
            )}
            {editing && (
              <Button
                size="sm"
                className="ml-auto gap-1"
                onClick={() => save.mutate()}
                disabled={!validJson || save.isPending}
              >
                <Save size={12} />
                Save
              </Button>
            )}
          </div>

          {isFilesystem && editing && (
            <div className="rounded-lg border border-amber-500/30 bg-amber-500/5 p-3 text-xs text-amber-300">
              Saving will create a DB override for this built-in definition. The original file remains unchanged. Delete the override to restore the built-in version.
            </div>
          )}

          <div>
            <Label className="text-caption font-semibold uppercase tracking-widest text-text-tertiary">Frontmatter</Label>
            {editing ? (
              <div className="relative mt-1">
                <Textarea
                  className="font-mono text-xs min-h-[120px]"
                  value={frontmatter}
                  onChange={(e) => setFrontmatter(e.target.value)}
                />
                {!validJson && (
                  <p className="mt-1 text-xs text-red-400">Invalid JSON</p>
                )}
              </div>
            ) : (
              <pre className="mt-1 max-h-48 overflow-auto rounded-lg bg-bg-hover p-3 font-mono text-xs text-text-secondary">
                {JSON.stringify(definition.frontmatter, null, 2)}
              </pre>
            )}
          </div>

          <div>
            <Label className="text-caption font-semibold uppercase tracking-widest text-text-tertiary">Body (Markdown)</Label>
            {editing ? (
              <Textarea
                className="mt-1 font-mono text-xs min-h-[200px]"
                value={body}
                onChange={(e) => setBody(e.target.value)}
              />
            ) : (
              <pre className="mt-1 max-h-64 overflow-auto whitespace-pre-wrap rounded-lg bg-bg-hover p-3 font-mono text-xs text-text-secondary">
                {definition.body || "(empty)"}
              </pre>
            )}
          </div>
        </div>
      </DialogContent>
    </Dialog>
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
