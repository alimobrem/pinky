"use client";

import { useParams, useRouter } from "next/navigation";
import { ArrowLeft } from "lucide-react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import type { Execution } from "@pinky/contracts";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import { ExecutionMonitor } from "@/components/execution-monitor";
import { relativeTime } from "@/lib/format-date";

const STATUS_VARIANT: Record<string, "default" | "secondary" | "destructive" | "outline"> = {
  pending: "secondary", running: "secondary", completed: "default", failed: "destructive",
};

export default function ExecutionDetailPage() {
  const params = useParams();
  const router = useRouter();
  const queryClient = useQueryClient();
  const taskId = params.id as string;
  const execId = params.execId as string;

  const { data: execution, isLoading } = useQuery({
    queryKey: ["execution", execId],
    queryFn: () => api.get<Execution>(`/api/v1/executions/${execId}`),
  });

  const handleComplete = () => queryClient.invalidateQueries({ queryKey: ["execution", execId] });

  if (isLoading) {
    return (
      <div className="flex flex-col gap-4">
        <div className="skeleton h-10 rounded-lg" />
        <div className="skeleton h-[300px] rounded-lg" />
      </div>
    );
  }

  if (!execution) return <div className="text-center text-text-tertiary py-16">Execution not found.</div>;

  return (
    <div>
      <div className="flex items-center mb-5">
        <Button variant="ghost" size="sm" onClick={() => router.push(`/tasks/${taskId}`)} className="gap-2 text-text-secondary hover:text-text-primary">
          <ArrowLeft size={16} /> Back to Task
        </Button>
      </div>

      <div className="mb-6">
        <h1 className="text-xl font-bold tracking-tight mb-3">Execution</h1>
        <div className="flex gap-3 items-center">
          <Badge variant={STATUS_VARIANT[execution.status] || "outline"}>{execution.status}</Badge>
          <span className="text-xs px-1.5 py-0.5 bg-bg-elevated rounded-sm text-text-secondary">{execution.execution_type}</span>
          <span className="text-xs text-text-tertiary">Started {execution.started_at ? relativeTime(execution.started_at) : "pending"}</span>
        </div>
      </div>

      <ExecutionMonitor executionId={execId} onComplete={handleComplete} />
    </div>
  );
}
