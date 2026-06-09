"use client";

import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useRetryableMutation } from "@/hooks/use-retryable-mutation";
import { api } from "@/lib/api";
import { QUERY_KEYS } from "@/lib/constants";
import { webhooksOptions } from "../queries";
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
import { Plus, Webhook } from "lucide-react";
import { DeleteButton } from "./delete-button";
import { toast } from "sonner";

export function WebhooksTab() {
  const qc = useQueryClient();
  const { data } = useQuery(webhooksOptions());
  const [createOpen, setCreateOpen] = useState(false);

  const del = useRetryableMutation({
    errorMessage: "Failed to delete webhook",
    mutationFn: (id: string) => api.del(`/api/v1/webhook-subscriptions/${id}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: QUERY_KEYS.webhooks() });
      toast.success("Webhook deleted");
    },
  });

  return (
    <FadeIn>
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle className="text-sm">Webhooks</CardTitle>
          <CreateWebhookDialog open={createOpen} onOpenChange={setCreateOpen} />
        </CardHeader>
        <CardContent>
          {(data?.items ?? []).length === 0 ? (
            <EmptyState icon={Webhook} title="No webhooks" description="Send event notifications to external systems" />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>URL</TableHead>
                  <TableHead>Events</TableHead>
                  <TableHead>Enabled</TableHead>
                  <TableHead className="w-12" />
                </TableRow>
              </TableHeader>
              <TableBody>
                {(data?.items ?? []).map((w) => (
                  <TableRow key={w.id}>
                    <TableCell className="font-medium">{w.name}</TableCell>
                    <TableCell className="max-w-[200px] truncate font-mono text-xs text-text-tertiary">{w.url}</TableCell>
                    <TableCell className="text-caption text-text-secondary">{w.event_patterns.join(", ")}</TableCell>
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

function CreateWebhookDialog({ open, onOpenChange }: { open: boolean; onOpenChange: (open: boolean) => void }) {
  const qc = useQueryClient();
  const [name, setName] = useState("");
  const [url, setUrl] = useState("");
  const [events, setEvents] = useState("");
  const [formatter, setFormatter] = useState("generic");
  const [channelConfig, setChannelConfig] = useState("");

  const create = useRetryableMutation({
    errorMessage: "Failed to create webhook",
    mutationFn: () => {
      const body: Record<string, unknown> = {
        name,
        url,
        event_patterns: events.split(",").map((e) => e.trim()).filter(Boolean),
        formatter,
      };
      if (channelConfig.trim()) {
        body.channel_config = JSON.parse(channelConfig);
      }
      return api.post("/api/v1/webhook-subscriptions", body);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: QUERY_KEYS.webhooks() });
      setName(""); setUrl(""); setEvents(""); setChannelConfig("");
      onOpenChange(false);
      toast.success("Webhook created");
    },
  });

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogTrigger asChild>
        <Button size="sm" className="gap-1"><Plus size={14} />Create</Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader><DialogTitle>Create Webhook</DialogTitle></DialogHeader>
        <div className="space-y-3">
          <div>
            <Label className="text-xs text-text-secondary">Name</Label>
            <Input className="mt-1" value={name} onChange={(e) => setName(e.target.value)} placeholder="slack-alerts" />
          </div>
          <div>
            <Label className="text-xs text-text-secondary">URL</Label>
            <Input className="mt-1" value={url} onChange={(e) => setUrl(e.target.value)} placeholder="https://hooks.slack.com/..." />
          </div>
          <div>
            <Label className="text-xs text-text-secondary">Event Patterns (comma-separated)</Label>
            <Input className="mt-1" value={events} onChange={(e) => setEvents(e.target.value)} placeholder="issue.*, work_item.blocked" />
          </div>
          <div>
            <Label className="text-xs text-text-secondary">Formatter</Label>
            <Select value={formatter} onValueChange={setFormatter}>
              <SelectTrigger className="mt-1"><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="generic">Generic</SelectItem>
                <SelectItem value="slack">Slack</SelectItem>
                <SelectItem value="pagerduty">PagerDuty</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div>
            <Label className="text-xs text-text-secondary">Channel Config (optional JSON)</Label>
            <Textarea className="mt-1 font-mono text-xs" rows={2} value={channelConfig} onChange={(e) => setChannelConfig(e.target.value)} placeholder='{"channel": "#ops-alerts"}' />
          </div>
          <Button onClick={() => create.mutate()} disabled={!name || !url || !events || create.isPending} className="w-full">
            Create Webhook
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
