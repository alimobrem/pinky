"use client";

import { useState } from "react";
import type { RemediationStep } from "@pinky/contracts";
import { cn } from "@/lib/utils";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
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
import {
  Play,
  Copy,
  Check,
  Code,
  Terminal,
  AlertTriangle,
  CheckCircle2,
} from "lucide-react";
import { toast } from "sonner";

interface RemediationPlanProps {
  steps: RemediationStep[];
  manualCommands: string[];
  clusterName?: string;
  onApply?: (steps: RemediationStep[]) => void;
  applyPending?: boolean;
}

const RISK_CONFIG = {
  low: { label: "Low Risk", color: "text-status-done", bg: "bg-status-done/10" },
  medium: { label: "Medium Risk", color: "text-status-in-progress", bg: "bg-status-in-progress/10" },
  high: { label: "High Risk", color: "text-status-blocked", bg: "bg-status-blocked/10" },
};

export function RemediationPlan({
  steps,
  manualCommands,
  clusterName,
  onApply,
  applyPending,
}: RemediationPlanProps) {
  const [selectedSteps, setSelectedSteps] = useState<Set<number>>(
    new Set(steps.map((_, i) => i)),
  );
  const [yamlStep, setYamlStep] = useState<RemediationStep | null>(null);

  if (steps.length === 0 && manualCommands.length === 0) return null;

  const toggleStep = (idx: number) => {
    const next = new Set(selectedSteps);
    if (next.has(idx)) next.delete(idx);
    else next.add(idx);
    setSelectedSteps(next);
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    toast.success("Copied to clipboard");
  };

  const selectedForApply = steps.filter((_, i) => selectedSteps.has(i));

  return (
    <div className="space-y-4">
      {steps.length > 0 && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center justify-between text-caption font-semibold uppercase tracking-widest text-text-tertiary">
              <span className="flex items-center gap-2">
                <Play size={14} className="text-brand-purple" />
                Recommended Actions
              </span>
              <span className="text-caption font-normal normal-case text-text-tertiary">
                {selectedSteps.size} of {steps.length} selected
              </span>
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {steps.map((step, i) => (
              <StepRow
                key={i}
                step={step}
                index={i}
                selected={selectedSteps.has(i)}
                onToggle={() => toggleStep(i)}
                onViewYaml={() => setYamlStep(step)}
                onCopyCommand={() => copyToClipboard(stepToCommand(step))}
              />
            ))}

            {onApply && selectedForApply.length > 0 && (
              <div className="flex gap-2 pt-3 border-t border-border-default">
                <AlertDialog>
                  <AlertDialogTrigger asChild>
                    <Button
                      className="flex-1 gap-2"
                      disabled={applyPending}
                    >
                      <Play size={14} />
                      {applyPending
                        ? "Applying..."
                        : `Apply ${selectedForApply.length} Step${selectedForApply.length !== 1 ? "s" : ""}`}
                    </Button>
                  </AlertDialogTrigger>
                  <AlertDialogContent>
                    <AlertDialogHeader>
                      <AlertDialogTitle>Apply remediation?</AlertDialogTitle>
                      <AlertDialogDescription>
                        {selectedForApply.length} action{selectedForApply.length !== 1 ? "s" : ""} will be
                        executed on {clusterName ?? "the cluster"}:
                      </AlertDialogDescription>
                    </AlertDialogHeader>
                    <div className="space-y-1.5 py-2">
                      {selectedForApply.map((step, i) => (
                        <div key={i} className="flex items-center gap-2 text-sm">
                          <RiskBadge risk={step.risk} />
                          <span className="text-text-primary">{step.description}</span>
                        </div>
                      ))}
                    </div>
                    <AlertDialogFooter>
                      <AlertDialogCancel>Cancel</AlertDialogCancel>
                      <AlertDialogAction
                        className="bg-brand-pink text-text-inverse hover:bg-brand-pink-dim"
                        onClick={() => onApply(selectedForApply)}
                      >
                        Approve & Execute
                      </AlertDialogAction>
                    </AlertDialogFooter>
                  </AlertDialogContent>
                </AlertDialog>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {manualCommands.length > 0 && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2 text-caption font-semibold uppercase tracking-widest text-text-tertiary">
              <Terminal size={14} className="text-text-tertiary" />
              Manual Commands
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-1.5">
            {manualCommands.map((cmd, i) => (
              <div
                key={i}
                className="group flex items-center gap-2 rounded-lg bg-bg-hover px-3 py-2"
              >
                <span className="text-text-tertiary">$</span>
                <code className="flex-1 font-mono text-xs text-brand-purple">
                  {cmd}
                </code>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-6 w-6 opacity-0 transition-opacity group-hover:opacity-100"
                  onClick={() => copyToClipboard(cmd)}
                >
                  <Copy size={12} />
                </Button>
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      <Dialog open={!!yamlStep} onOpenChange={(open) => !open && setYamlStep(null)}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>{yamlStep?.description}</DialogTitle>
          </DialogHeader>
          {yamlStep && (
            <div className="space-y-3">
              <div className="flex items-center gap-2 text-sm text-text-secondary">
                <RiskBadge risk={yamlStep.risk} />
                <span>{yamlStep.resource_kind}/{yamlStep.resource_name}</span>
                <span className="text-text-tertiary">in {yamlStep.resource_namespace}</span>
              </div>
              <div className="relative">
                <pre className="rounded-lg bg-bg-hover p-4 font-mono text-xs text-text-primary overflow-auto max-h-64">
                  {stepToYaml(yamlStep)}
                </pre>
                <Button
                  variant="ghost"
                  size="icon"
                  className="absolute right-2 top-2 h-7 w-7"
                  onClick={() => copyToClipboard(stepToYaml(yamlStep))}
                >
                  <Copy size={14} />
                </Button>
              </div>
              <div>
                <p className="text-caption text-text-tertiary mb-1">Equivalent command</p>
                <div className="flex items-center gap-2 rounded-lg bg-bg-hover px-3 py-2">
                  <code className="flex-1 font-mono text-xs text-brand-purple">
                    {stepToCommand(yamlStep)}
                  </code>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-6 w-6"
                    onClick={() => copyToClipboard(stepToCommand(yamlStep))}
                  >
                    <Copy size={12} />
                  </Button>
                </div>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}

function StepRow({
  step,
  index,
  selected,
  onToggle,
  onViewYaml,
  onCopyCommand,
}: {
  step: RemediationStep;
  index: number;
  selected: boolean;
  onToggle: () => void;
  onViewYaml: () => void;
  onCopyCommand: () => void;
}) {
  return (
    <div
      className={cn(
        "flex items-center gap-3 rounded-lg border px-3 py-2.5 transition-colors",
        selected
          ? "border-brand-purple/30 bg-brand-purple/5"
          : "border-border-default bg-bg-surface",
      )}
    >
      <button
        type="button"
        className={cn(
          "flex h-5 w-5 shrink-0 items-center justify-center rounded border transition-colors",
          selected
            ? "border-brand-purple bg-brand-purple text-white"
            : "border-border-strong bg-transparent",
        )}
        onClick={onToggle}
      >
        {selected && <Check size={12} />}
      </button>

      <div className="min-w-0 flex-1">
        <p className="text-sm font-medium text-text-primary">{step.description}</p>
        <p className="mt-0.5 font-mono text-caption text-text-tertiary">
          {step.resource_kind}/{step.resource_name} in {step.resource_namespace}
        </p>
      </div>

      <RiskBadge risk={step.risk} />

      <div className="flex items-center gap-1">
        <Button
          variant="ghost"
          size="icon"
          className="h-7 w-7 text-text-tertiary hover:text-text-secondary"
          onClick={onViewYaml}
          title="View YAML"
        >
          <Code size={14} />
        </Button>
        <Button
          variant="ghost"
          size="icon"
          className="h-7 w-7 text-text-tertiary hover:text-text-secondary"
          onClick={onCopyCommand}
          title="Copy command"
        >
          <Copy size={14} />
        </Button>
      </div>
    </div>
  );
}

function RiskBadge({ risk }: { risk: string }) {
  const config = RISK_CONFIG[risk as keyof typeof RISK_CONFIG] ?? RISK_CONFIG.medium;
  return (
    <Badge variant="outline" className={cn("text-caption", config.color, config.bg)}>
      {config.label}
    </Badge>
  );
}

function stepToCommand(step: RemediationStep): string {
  const ns = step.resource_namespace ? `-n ${step.resource_namespace}` : "";
  switch (step.action) {
    case "scale": {
      const replicas = (step.params as Record<string, number>).replicas ?? 3;
      return `oc scale ${step.resource_kind.toLowerCase()}/${step.resource_name} ${ns} --replicas=${replicas}`;
    }
    case "delete_pod":
      return `oc delete pod ${step.resource_name} ${ns}`;
    case "patch":
      return `oc patch ${step.resource_kind.toLowerCase()}/${step.resource_name} ${ns} -p '${JSON.stringify(step.params)}'`;
    case "rollback":
      return `oc rollout undo ${step.resource_kind.toLowerCase()}/${step.resource_name} ${ns}`;
    default:
      return `oc ${step.action} ${step.resource_kind.toLowerCase()}/${step.resource_name} ${ns}`;
  }
}

function stepToYaml(step: RemediationStep): string {
  const params = step.params as Record<string, unknown>;
  switch (step.action) {
    case "scale":
      return [
        `apiVersion: apps/v1`,
        `kind: ${step.resource_kind}`,
        `metadata:`,
        `  name: ${step.resource_name}`,
        `  namespace: ${step.resource_namespace}`,
        `spec:`,
        `  replicas: ${params.replicas ?? 3}`,
      ].join("\n");
    case "patch":
      return [
        `# Patch for ${step.resource_kind}/${step.resource_name}`,
        `# Namespace: ${step.resource_namespace}`,
        ``,
        JSON.stringify(params, null, 2),
      ].join("\n");
    case "delete_pod":
      return [
        `# Delete pod`,
        `apiVersion: v1`,
        `kind: Pod`,
        `metadata:`,
        `  name: ${step.resource_name}`,
        `  namespace: ${step.resource_namespace}`,
      ].join("\n");
    default:
      return JSON.stringify(step, null, 2);
  }
}
