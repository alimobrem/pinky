"use client";

import { useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft } from "lucide-react";
import { api } from "@/lib/api";
import { QUERY_KEYS } from "@/lib/constants";
import { executionOptions, executionEventsOptions } from "../queries";
import { ExecutionMonitor } from "@/components/shared/execution-monitor";
import { ExecutionTerminal } from "@/components/shared/execution-terminal";
import { StatusIndicator } from "@/components/shared/status-indicator";
import { PageHeader } from "@/components/shared/page-header";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { useEventBus } from "@/hooks/use-event-bus";
import { toast } from "sonner";

interface ExecutionDetailViewProps {
  taskId: string;
  execId: string;
}

export function ExecutionDetailView({ taskId, execId }: ExecutionDetailViewProps) {
  const router = useRouter();
  const qc = useQueryClient();

  const { data: execution } = useQuery(executionOptions(execId));
  const { data: events } = useQuery(executionEventsOptions(taskId));

  const invalidateAll = () => {
    qc.invalidateQueries({ queryKey: QUERY_KEYS.execution(execId) });
    qc.invalidateQueries({ queryKey: QUERY_KEYS.taskTimeline(taskId) });
  };

  useEventBus("execution-detail", (envelope) => {
    if (envelope.payload?.execution_id === execId || envelope.aggregate_id === execId) {
      invalidateAll();
    }
  });

  const approve = useMutation({
    mutationFn: (id: string) => api.post(`/api/v1/executions/${id}/approve`),
    onSuccess: () => { invalidateAll(); toast.success("Approved"); },
  });
  const reject = useMutation({
    mutationFn: (id: string) => api.post(`/api/v1/executions/${id}/reject`),
    onSuccess: () => { invalidateAll(); toast.success("Rejected"); },
  });

  if (!execution) return null;

  const isRemediation = execution.execution_type === "remediation";
  const execEvents = (events?.items ?? []).filter(
    (e: { execution_id: string }) => e.execution_id === execId,
  );

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <Button
          variant="ghost"
          size="icon"
          className="h-8 w-8"
          onClick={() => router.back()}
        >
          <ArrowLeft size={16} />
        </Button>
        <PageHeader
          title={`Execution: ${execution.execution_type}`}
          meta={<StatusIndicator status={execution.status} />}
          className="mb-0 flex-1"
        />
      </div>

      <Card className="overflow-hidden">
        {isRemediation ? (
          <div className="p-4">
            <ExecutionTerminal events={execEvents} />
          </div>
        ) : (
          <ExecutionMonitor
            events={execEvents}
            sseState="connected"
            lastUpdated={null}
            pendingApproval={execution.status === "waiting_for_approval"}
            executionId={execId}
            onApprove={(id) => approve.mutate(id)}
            onReject={(id) => reject.mutate(id)}
          />
        )}
      </Card>
    </div>
  );
}
