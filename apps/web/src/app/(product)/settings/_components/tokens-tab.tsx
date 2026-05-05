"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import type { ApiTokenCreateResponse } from "@pinky/contracts";
import { api } from "@/lib/api";
import { QUERY_KEYS } from "@/lib/constants";
import { apiTokensOptions } from "../queries";
import { EmptyState } from "@/components/shared/empty-state";
import { RelativeTime } from "@/components/shared/relative-time";
import { FadeIn } from "@/components/motion/fade-in";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
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
import { Switch } from "@/components/ui/switch";
import { Key, Plus, Copy, Check, Trash2 } from "lucide-react";
import { toast } from "sonner";

const AVAILABLE_SCOPES = ["read", "write", "admin"] as const;

export function TokensTab() {
  const qc = useQueryClient();
  const { data } = useQuery(apiTokensOptions());
  const [createOpen, setCreateOpen] = useState(false);

  const revoke = useMutation({
    mutationFn: (id: string) => api.del(`/api/v1/api-tokens/${id}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: QUERY_KEYS.apiTokens() });
      toast.success("Token revoked");
    },
    onError: () => toast.error("Failed to revoke token"),
  });

  return (
    <FadeIn>
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle className="text-sm">API Tokens</CardTitle>
          <CreateTokenDialog open={createOpen} onOpenChange={setCreateOpen} />
        </CardHeader>
        <CardContent>
          {(data?.items ?? []).length === 0 ? (
            <EmptyState icon={Key} title="No API tokens" description="Create tokens for CLI and CI authentication" />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>Scopes</TableHead>
                  <TableHead>Created</TableHead>
                  <TableHead>Last Used</TableHead>
                  <TableHead className="w-20" />
                </TableRow>
              </TableHeader>
              <TableBody>
                {(data?.items ?? []).map((t) => (
                  <TableRow key={t.id}>
                    <TableCell className="font-medium">{t.name}</TableCell>
                    <TableCell>
                      <div className="flex gap-1">
                        {t.scopes.map((s) => (
                          <Badge key={s} variant="secondary" className="text-[10px]">{s}</Badge>
                        ))}
                        {t.scopes.length === 0 && <span className="text-xs text-text-tertiary">none</span>}
                      </div>
                    </TableCell>
                    <TableCell><RelativeTime date={t.created_at} /></TableCell>
                    <TableCell>
                      {t.last_used_at ? <RelativeTime date={t.last_used_at} /> : <span className="text-xs text-text-tertiary">Never</span>}
                    </TableCell>
                    <TableCell>
                      <AlertDialog>
                        <AlertDialogTrigger asChild>
                          <Button variant="ghost" size="icon" className="h-7 w-7 text-text-tertiary hover:text-status-blocked">
                            <Trash2 size={14} />
                          </Button>
                        </AlertDialogTrigger>
                        <AlertDialogContent>
                          <AlertDialogHeader>
                            <AlertDialogTitle>Revoke &ldquo;{t.name}&rdquo;?</AlertDialogTitle>
                            <AlertDialogDescription>This token will immediately stop working. This action cannot be undone.</AlertDialogDescription>
                          </AlertDialogHeader>
                          <AlertDialogFooter>
                            <AlertDialogCancel>Cancel</AlertDialogCancel>
                            <AlertDialogAction className="bg-destructive text-destructive-foreground" onClick={() => revoke.mutate(t.id)}>Revoke</AlertDialogAction>
                          </AlertDialogFooter>
                        </AlertDialogContent>
                      </AlertDialog>
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

function CreateTokenDialog({ open, onOpenChange }: { open: boolean; onOpenChange: (open: boolean) => void }) {
  const qc = useQueryClient();
  const [name, setName] = useState("");
  const [scopes, setScopes] = useState<Set<string>>(new Set());
  const [expiresAt, setExpiresAt] = useState("");
  const [createdToken, setCreatedToken] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const create = useMutation({
    mutationFn: () =>
      api.post<ApiTokenCreateResponse>("/api/v1/api-tokens", {
        name,
        scopes: [...scopes],
        expires_at: expiresAt || null,
      }),
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: QUERY_KEYS.apiTokens() });
      setCreatedToken(data.token);
      toast.success("Token created");
    },
    onError: () => toast.error("Failed to create token"),
  });

  function handleOpenChange(next: boolean) {
    if (!next) {
      setName("");
      setScopes(new Set());
      setExpiresAt("");
      setCreatedToken(null);
      setCopied(false);
    }
    onOpenChange(next);
  }

  function toggleScope(scope: string) {
    setScopes((prev) => {
      const next = new Set(prev);
      if (next.has(scope)) next.delete(scope);
      else next.add(scope);
      return next;
    });
  }

  async function copyToken() {
    if (!createdToken) return;
    await navigator.clipboard.writeText(createdToken);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogTrigger asChild>
        <Button size="sm" className="gap-1"><Plus size={14} />Create Token</Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader><DialogTitle>Create API Token</DialogTitle></DialogHeader>
        {createdToken ? (
          <div className="space-y-3">
            <div className="rounded-lg border border-yellow-500/30 bg-yellow-500/10 p-3">
              <p className="text-sm font-medium text-yellow-600 dark:text-yellow-400">
                Copy this token now. It won&apos;t be shown again.
              </p>
            </div>
            <div className="flex items-center gap-2">
              <code className="flex-1 overflow-x-auto rounded-lg bg-bg-hover p-3 font-mono text-xs text-text-secondary">
                {createdToken}
              </code>
              <Button variant="ghost" size="icon" className="h-8 w-8 shrink-0" onClick={copyToken}>
                {copied ? <Check size={14} className="text-green-500" /> : <Copy size={14} />}
              </Button>
            </div>
            <Button className="w-full" onClick={() => handleOpenChange(false)}>Done</Button>
          </div>
        ) : (
          <div className="space-y-3">
            <div>
              <Label className="text-xs text-text-secondary">Name</Label>
              <Input className="mt-1" value={name} onChange={(e) => setName(e.target.value)} placeholder="ci-deploy-token" />
            </div>
            <div>
              <Label className="text-xs text-text-secondary">Scopes</Label>
              <div className="mt-1.5 flex gap-3">
                {AVAILABLE_SCOPES.map((scope) => (
                  <label key={scope} className="flex items-center gap-1.5 text-sm">
                    <Switch checked={scopes.has(scope)} onCheckedChange={() => toggleScope(scope)} />
                    {scope}
                  </label>
                ))}
              </div>
            </div>
            <div>
              <Label className="text-xs text-text-secondary">Expires (optional)</Label>
              <Input className="mt-1" type="date" value={expiresAt} onChange={(e) => setExpiresAt(e.target.value)} />
            </div>
            <Button onClick={() => create.mutate()} disabled={!name || create.isPending} className="w-full">
              Create Token
            </Button>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
