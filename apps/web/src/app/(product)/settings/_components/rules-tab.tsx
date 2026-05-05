"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { QUERY_KEYS } from "@/lib/constants";
import { policyRulesOptions } from "../queries";
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
import { Plus, Shield, FlaskConical } from "lucide-react";
import { DeleteButton } from "./delete-button";
import { toast } from "sonner";

export function RulesTab() {
  const qc = useQueryClient();
  const { data } = useQuery(policyRulesOptions());
  const [createOpen, setCreateOpen] = useState(false);
  const [testOpen, setTestOpen] = useState(false);

  const del = useMutation({
    mutationFn: (id: string) => api.del(`/api/v1/policy-rules/${id}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: QUERY_KEYS.policyRules() });
      toast.success("Rule deleted");
    },
  });

  return (
    <FadeIn>
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle className="text-sm">Policy Rules</CardTitle>
          <div className="flex items-center gap-2">
            <TestRuleDialog open={testOpen} onOpenChange={setTestOpen} />
            <CreateRuleDialog open={createOpen} onOpenChange={setCreateOpen} />
          </div>
        </CardHeader>
        <CardContent>
          {(data?.items ?? []).length === 0 ? (
            <EmptyState icon={Shield} title="No rules" description="Policy rules control how the Brain responds to signals" />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>Description</TableHead>
                  <TableHead>Priority</TableHead>
                  <TableHead>Enabled</TableHead>
                  <TableHead className="w-12" />
                </TableRow>
              </TableHeader>
              <TableBody>
                {(data?.items ?? []).map((r) => (
                  <TableRow key={r.id}>
                    <TableCell className="font-medium">{r.name}</TableCell>
                    <TableCell className="max-w-[200px] truncate text-body-sm text-text-secondary">{r.description || "—"}</TableCell>
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

function CreateRuleDialog({ open, onOpenChange }: { open: boolean; onOpenChange: (open: boolean) => void }) {
  const qc = useQueryClient();
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [priority, setPriority] = useState("100");
  const [conditions, setConditions] = useState('{"severity": "critical"}');
  const [action, setAction] = useState('{"type": "investigate"}');

  const create = useMutation({
    mutationFn: () =>
      api.post("/api/v1/policy-rules", {
        name,
        description,
        priority: parseInt(priority, 10),
        conditions: JSON.parse(conditions),
        action: JSON.parse(action),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: QUERY_KEYS.policyRules() });
      setName(""); setDescription("");
      onOpenChange(false);
      toast.success("Rule created");
    },
    onError: () => toast.error("Failed to create rule"),
  });

  const validJson = (() => {
    try { JSON.parse(conditions); JSON.parse(action); return true; } catch { return false; }
  })();

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogTrigger asChild>
        <Button size="sm" className="gap-1"><Plus size={14} />Create</Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader><DialogTitle>Create Policy Rule</DialogTitle></DialogHeader>
        <div className="space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label className="text-xs text-text-secondary">Name</Label>
              <Input className="mt-1" value={name} onChange={(e) => setName(e.target.value)} placeholder="critical-auto-investigate" />
            </div>
            <div>
              <Label className="text-xs text-text-secondary">Priority</Label>
              <Input className="mt-1" type="number" value={priority} onChange={(e) => setPriority(e.target.value)} />
            </div>
          </div>
          <div>
            <Label className="text-xs text-text-secondary">Description</Label>
            <Input className="mt-1" value={description} onChange={(e) => setDescription(e.target.value)} placeholder="Auto-investigate critical severity signals" />
          </div>
          <div>
            <Label className="text-xs text-text-secondary">Conditions (JSON)</Label>
            <Textarea className="mt-1 font-mono text-xs" rows={3} value={conditions} onChange={(e) => setConditions(e.target.value)} />
          </div>
          <div>
            <Label className="text-xs text-text-secondary">Action (JSON)</Label>
            <Textarea className="mt-1 font-mono text-xs" rows={2} value={action} onChange={(e) => setAction(e.target.value)} />
          </div>
          <Button onClick={() => create.mutate()} disabled={!name || !validJson || create.isPending} className="w-full">
            Create Rule
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}

function TestRuleDialog({ open, onOpenChange }: { open: boolean; onOpenChange: (open: boolean) => void }) {
  const [input, setInput] = useState(JSON.stringify({
    scanner: "pod-health",
    check_id: "crash-loop",
    severity: "critical",
    resource_kind: "Pod",
    cluster_id: "",
    labels: {},
    recurrence_count: 1,
  }, null, 2));
  const [result, setResult] = useState<string | null>(null);

  const evaluate = useMutation({
    mutationFn: () => api.post<{ matched: boolean; rule_name?: string; action?: Record<string, unknown> }>("/api/v1/policy-rules/evaluate", JSON.parse(input)),
    onSuccess: (data) => setResult(JSON.stringify(data, null, 2)),
    onError: () => toast.error("Evaluation failed"),
  });

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogTrigger asChild>
        <Button size="sm" variant="outline" className="gap-1"><FlaskConical size={14} />Test</Button>
      </DialogTrigger>
      <DialogContent className="max-w-lg">
        <DialogHeader><DialogTitle>Test Policy Rules</DialogTitle></DialogHeader>
        <div className="space-y-3">
          <div>
            <Label className="text-xs text-text-secondary">Input (JSON)</Label>
            <Textarea className="mt-1 font-mono text-xs" rows={8} value={input} onChange={(e) => setInput(e.target.value)} />
          </div>
          <Button onClick={() => evaluate.mutate()} disabled={evaluate.isPending} className="w-full">
            Evaluate
          </Button>
          {result && (
            <div>
              <Label className="text-xs text-text-secondary">Result</Label>
              <pre className="mt-1 rounded-lg bg-bg-hover p-3 font-mono text-xs text-text-secondary">{result}</pre>
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
