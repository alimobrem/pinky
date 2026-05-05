"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { analyticsRoiOptions, analyticsScannersOptions } from "../queries";
import { EmptyState } from "@/components/shared/empty-state";
import { FadeIn } from "@/components/motion/fade-in";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Progress } from "@/components/ui/progress";
import {
  BarChart3,
  CheckCircle2,
  ListTodo,
  TrendingUp,
  AlertTriangle,
  Zap,
  Target,
} from "lucide-react";
import { cn } from "@/lib/utils";

const PERIODS = [
  { label: "7d", value: "7d" },
  { label: "30d", value: "30d" },
  { label: "90d", value: "90d" },
] as const;

export function AnalyticsTab() {
  const [period, setPeriod] = useState("30d");
  const { data: roi } = useQuery(analyticsRoiOptions(period));
  const { data: scanners } = useQuery(analyticsScannersOptions(period));
  const m = roi?.metrics;

  const completionRate = m ? Math.round(m.task_completion_rate * 100) : 0;
  const resolutionRate = m && m.issues_total > 0 ? Math.round((m.issues_resolved / m.issues_total) * 100) : 0;

  return (
    <FadeIn>
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-medium text-text-primary">Platform Analytics</h3>
          <div className="flex gap-1 rounded-lg border border-border-default p-0.5">
            {PERIODS.map((p) => (
              <Button
                key={p.value}
                size="sm"
                variant={period === p.value ? "default" : "ghost"}
                className="h-6 px-3 text-xs"
                onClick={() => setPeriod(p.value)}
              >
                {p.label}
              </Button>
            ))}
          </div>
        </div>

        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <StatCard
            icon={AlertTriangle}
            label="Issues Detected"
            value={m?.issues_total ?? 0}
            sub={`${m?.issues_resolved ?? 0} resolved`}
            color="text-status-blocked"
          />
          <StatCard
            icon={CheckCircle2}
            label="Issues Resolved"
            value={m?.issues_resolved ?? 0}
            sub={`${resolutionRate}% resolution rate`}
            color="text-status-done"
          />
          <StatCard
            icon={ListTodo}
            label="Tasks Created"
            value={m?.tasks_total ?? 0}
            sub={`${m?.tasks_completed ?? 0} completed`}
            color="text-status-ready"
          />
          <StatCard
            icon={Target}
            label="Tasks Completed"
            value={m?.tasks_completed ?? 0}
            sub={`${completionRate}% completion rate`}
            color="text-status-done"
          />
          <StatCard
            icon={Zap}
            label="Executions"
            value={m?.executions_total ?? 0}
            sub="investigations + remediations"
            color="text-brand-purple"
          />
          <StatCard
            icon={TrendingUp}
            label="Completion Rate"
            value={completionRate}
            suffix="%"
            color="text-status-in-progress"
            progress={completionRate}
          />
        </div>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle className="text-sm">Scanner Activity</CardTitle>
            <span className="text-caption text-text-tertiary">Last {period}</span>
          </CardHeader>
          <CardContent>
            {!scanners?.scanners?.length ? (
              <EmptyState icon={BarChart3} title="No data" description="Scanner metrics will appear after first scan" />
            ) : (
              <div className="space-y-3">
                {scanners.scanners
                  .sort((a, b) => b.signal_total - a.signal_total)
                  .map((s) => {
                    const max = Math.max(...scanners.scanners.map((x) => x.signal_total));
                    const pct = max > 0 ? (s.signal_total / max) * 100 : 0;
                    return (
                      <div key={s.scanner} className="space-y-1">
                        <div className="flex items-center justify-between text-sm">
                          <span className="font-mono text-text-secondary">{s.scanner}</span>
                          <span className="font-mono tabular-nums text-text-primary">{s.signal_total}</span>
                        </div>
                        <div className="h-1.5 rounded-full bg-bg-hover">
                          <div
                            className="h-full rounded-full bg-brand-purple transition-all duration-500"
                            style={{ width: `${pct}%` }}
                          />
                        </div>
                      </div>
                    );
                  })}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </FadeIn>
  );
}

function StatCard({
  icon: Icon,
  label,
  value,
  sub,
  suffix,
  color,
  progress: progressValue,
}: {
  icon: typeof BarChart3;
  label: string;
  value: number;
  sub?: string;
  suffix?: string;
  color: string;
  progress?: number;
}) {
  return (
    <Card>
      <CardContent className="p-4">
        <div className="flex items-center gap-2">
          <div className={cn("rounded-lg bg-bg-hover p-1.5", color)}>
            <Icon size={14} />
          </div>
          <span className="text-caption text-text-tertiary">{label}</span>
        </div>
        <p className="mt-2 font-mono text-2xl font-bold tabular-nums text-text-primary">
          {value}{suffix}
        </p>
        {sub && <p className="mt-0.5 text-caption text-text-tertiary">{sub}</p>}
        {progressValue != null && (
          <Progress value={progressValue} className="mt-2 h-1.5" />
        )}
      </CardContent>
    </Card>
  );
}
