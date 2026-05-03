"use client";

import { useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { Brain, Eye, EyeOff, CheckCircle } from "lucide-react";
import { toast } from "sonner";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import type { Issue, PaginatedResponse } from "@pinky/contracts";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useSSE } from "@/hooks/use-sse";
import { api } from "@/lib/api";
import { relativeTime } from "@/lib/format-date";
import { SEVERITY_VARIANT, SEVERITY_BORDER } from "@/lib/status-colors";

export default function WatchPage() {
  const searchParams = useSearchParams();
  const cluster = searchParams.get("cluster");
  const queryClient = useQueryClient();
  const [actingId, setActingId] = useState<string | null>(null);

  const queryKey = ["issues", cluster] as const;
  const { data, error: fetchError } = useQuery({
    queryKey,
    queryFn: () => {
      let url = "/api/v1/issues?status=open";
      if (cluster && cluster !== "all") url += `&cluster_id=${cluster}`;
      return api.get<PaginatedResponse<Issue>>(url);
    },
  });

  const issues = data?.items ?? [];

  const sseHandlers = useMemo(() => ({
    update: () => queryClient.invalidateQueries({ queryKey: ["issues"] }),
  }), [queryClient]);

  const { state: sseState, lastUpdated } = useSSE("/api/v1/streams/watch", { onEvent: sseHandlers });
  const connected = sseState === "connected";

  const suppressMutation = useMutation({
    mutationFn: (id: string) => { setActingId(id); return api.post(`/api/v1/issues/${id}/suppress`, {}); },
    onSuccess: () => { toast.success("Issue suppressed"); queryClient.invalidateQueries({ queryKey: ["issues"] }); },
    onError: (e: Error) => toast.error(e.message),
    onSettled: () => setActingId(null),
  });

  const resolveMutation = useMutation({
    mutationFn: (id: string) => { setActingId(id); return api.post(`/api/v1/issues/${id}/resolve`); },
    onSuccess: () => { toast.success("Issue resolved"); queryClient.invalidateQueries({ queryKey: ["issues"] }); },
    onError: (e: Error) => toast.error(e.message),
    onSettled: () => setActingId(null),
  });

  return (
    <div>
      <div className="flex items-center gap-3 mb-5">
        <Eye size={20} className="text-text-tertiary" />
        <h1 className="text-xl font-semibold tracking-tight">Watch</h1>
      </div>

      <div className="flex items-center gap-2 mb-6 text-xs text-text-tertiary">
        <span className={`w-2 h-2 rounded-full inline-block ${connected ? "bg-status-done animate-brain-pulse" : "bg-status-blocked"}`} />
        {connected ? `Live — updated ${lastUpdated ? relativeTime(lastUpdated.toISOString()) : ""}` : sseState === "reconnecting" ? "Reconnecting..." : "Connecting..."}
      </div>

      {fetchError && (
        <div className="p-3 px-4 mb-4 rounded-md bg-status-blocked/10 border border-status-blocked/30 text-status-blocked text-sm">{fetchError.message}</div>
      )}

      {issues.length === 0 && !fetchError ? (
        <div className="flex flex-col items-center py-16 px-6 text-center">
          <div className="font-mono text-xl text-text-tertiary mb-6">~ ~ ~</div>
          <div className="text-[15px] font-semibold text-text-primary mb-2">All quiet on the western cluster.</div>
          <div className="text-sm text-text-secondary leading-relaxed">The Brain is monitoring but has nothing to escalate right now.</div>
        </div>
      ) : issues.length > 0 ? (
        <div className="flex flex-col gap-2">
          {issues.map(issue => (
            <div key={issue.id} className={`bg-bg-surface border border-border-default rounded-lg p-4 px-5 border-l-3 ${SEVERITY_BORDER[issue.severity] || "border-l-border-default"} transition-colors`}>
              <div className="flex justify-between items-center">
                <div className="flex items-center gap-2 flex-1">
                  <Brain size={14} className="text-accent-brain" />
                  <span className="font-semibold text-sm">{issue.title}</span>
                </div>
                <Badge variant={SEVERITY_VARIANT[issue.severity] || "outline"} className="uppercase text-[11px]">{issue.severity}</Badge>
              </div>
              <div className="text-xs text-text-tertiary mt-2 pl-6">
                {issue.status} — last seen {issue.last_seen_at ? relativeTime(issue.last_seen_at) : "unknown"}
              </div>
              <div className="flex gap-2 mt-3 pl-6">
                <Button variant="outline" size="sm" onClick={() => suppressMutation.mutate(issue.id)} disabled={actingId === issue.id} className="h-7 text-xs">
                  <EyeOff size={12} /> Suppress
                </Button>
                <Button variant="outline" size="sm" onClick={() => resolveMutation.mutate(issue.id)} disabled={actingId === issue.id} className="h-7 text-xs text-status-done">
                  <CheckCircle size={12} /> Resolve
                </Button>
                <Button variant="outline" size="sm" asChild className="h-7 text-xs">
                  <Link href={`/tasks?cluster=${issue.cluster_id}`}>View tasks</Link>
                </Button>
              </div>
            </div>
          ))}
        </div>
      ) : null}
    </div>
  );
}
