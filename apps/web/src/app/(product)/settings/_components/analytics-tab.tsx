"use client";

import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { analyticsRoiOptions, analyticsScannersOptions, analyticsTrendsOptions } from "../queries";
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
  Coins,
  Database,
  ArrowUpDown,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { ResponsiveContainer, AreaChart, Area } from "recharts";

const PERIODS = [
  { label: "7d", value: "7d" },
  { label: "30d", value: "30d" },
  { label: "90d", value: "90d" },
] as const;

export function AnalyticsTab() {
  const [period, setPeriod] = useState("30d");
  const [sortField, setSortField] = useState<keyof ScannerMetric>("signal_total");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");

  const { data: roi } = useQuery(analyticsRoiOptions(period));
  const { data: scanners } = useQuery(analyticsScannersOptions(period));
  const { data: tokenTrend } = useQuery(analyticsTrendsOptions("token_usage", period, "day"));
  const { data: cacheHitTrend } = useQuery(analyticsTrendsOptions("cache_hit_rate", period, "day"));

  const m = roi?.metrics;
  const completionRate = m ? Math.round(m.task_completion_rate * 100) : 0;
  const resolutionRate = m && m.issues_total > 0 ? Math.round((m.issues_resolved / m.issues_total) * 100) : 0;

  const tokenChartData = useMemo(
    () =>
      tokenTrend?.buckets.map((b) => ({
        timestamp: b.timestamp,
        total: (b.input_tokens ?? 0) + (b.output_tokens ?? 0),
      })) ?? [],
    [tokenTrend]
  );

  const cacheChartData = useMemo(
    () =>
      cacheHitTrend?.buckets.map((b) => ({
        timestamp: b.timestamp,
        rate: b.value ?? 0,
      })) ?? [],
    [cacheHitTrend]
  );

  const totalTokens = useMemo(
    () => tokenChartData.reduce((sum, d) => sum + d.total, 0),
    [tokenChartData]
  );

  const avgCacheHitRate = useMemo(
    () =>
      cacheChartData.length > 0
        ? Math.round((cacheChartData.reduce((sum, d) => sum + d.rate, 0) / cacheChartData.length) * 100)
        : 0,
    [cacheChartData]
  );

  const sortedScanners = useMemo(() => {
    if (!scanners?.scanners) return [];
    const list = [...scanners.scanners];
    list.sort((a, b) => {
      const aVal = a[sortField];
      const bVal = b[sortField];
      const dir = sortDir === "asc" ? 1 : -1;
      return aVal < bVal ? -dir : aVal > bVal ? dir : 0;
    });
    return list;
  }, [scanners, sortField, sortDir]);

  const handleSort = (field: keyof ScannerMetric) => {
    if (sortField === field) {
      setSortDir(sortDir === "asc" ? "desc" : "asc");
    } else {
      setSortField(field);
      setSortDir("desc");
    }
  };

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

        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <StatCard
            icon={AlertTriangle}
            label="Issues Detected"
            value={m?.issues_total ?? 0}
            sub={`${resolutionRate}% resolved`}
            color="text-status-blocked"
          />
          <StatCard
            icon={ListTodo}
            label="Tasks Created"
            value={m?.tasks_total ?? 0}
            sub={`${completionRate}% completed`}
            color="text-status-ready"
          />
          <StatCard
            icon={Zap}
            label="Executions"
            value={m?.executions_total ?? 0}
            sub="total workflows"
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

        <div className="grid gap-4 sm:grid-cols-2">
          <Card>
            <CardHeader>
              <div className="flex items-center gap-2">
                <div className="rounded-lg bg-bg-hover p-1.5 text-brand-purple">
                  <Coins size={14} />
                </div>
                <CardTitle className="text-sm">Token Usage</CardTitle>
              </div>
            </CardHeader>
            <CardContent>
              <p className="font-mono text-2xl font-bold tabular-nums text-text-primary">
                {totalTokens.toLocaleString()}
              </p>
              <p className="mt-0.5 text-caption text-text-tertiary">total tokens (in+out)</p>
              {tokenChartData.length > 0 && (
                <div className="mt-3 h-[60px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={tokenChartData}>
                      <defs>
                        <linearGradient id="tokenGradient" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="0%" stopColor="rgb(139, 92, 246)" stopOpacity={0.3} />
                          <stop offset="100%" stopColor="rgb(139, 92, 246)" stopOpacity={0} />
                        </linearGradient>
                      </defs>
                      <Area
                        type="monotone"
                        dataKey="total"
                        stroke="rgb(139, 92, 246)"
                        strokeWidth={1.5}
                        fill="url(#tokenGradient)"
                        isAnimationActive={false}
                      />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <div className="flex items-center gap-2">
                <div className="rounded-lg bg-bg-hover p-1.5 text-status-done">
                  <Database size={14} />
                </div>
                <CardTitle className="text-sm">Cache Hit Rate</CardTitle>
              </div>
            </CardHeader>
            <CardContent>
              <p className="font-mono text-2xl font-bold tabular-nums text-text-primary">
                {avgCacheHitRate}%
              </p>
              <p className="mt-0.5 text-caption text-text-tertiary">average hit rate</p>
              {cacheChartData.length > 0 && (
                <div className="mt-3 h-[60px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={cacheChartData}>
                      <defs>
                        <linearGradient id="cacheGradient" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="0%" stopColor="rgb(34, 197, 94)" stopOpacity={0.3} />
                          <stop offset="100%" stopColor="rgb(34, 197, 94)" stopOpacity={0} />
                        </linearGradient>
                      </defs>
                      <Area
                        type="monotone"
                        dataKey="rate"
                        stroke="rgb(34, 197, 94)"
                        strokeWidth={1.5}
                        fill="url(#cacheGradient)"
                        isAnimationActive={false}
                      />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Scanner Quality</CardTitle>
          </CardHeader>
          <CardContent>
            {!scanners?.scanners?.length ? (
              <EmptyState icon={BarChart3} title="No data" description="Scanner metrics will appear after first scan" />
            ) : (
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>
                        <button
                          className="flex items-center gap-1 text-caption font-medium text-text-tertiary hover:text-text-primary"
                          onClick={() => handleSort("scanner")}
                        >
                          Scanner
                          <ArrowUpDown size={12} />
                        </button>
                      </TableHead>
                      <TableHead className="text-right">
                        <button
                          className="flex items-center justify-end gap-1 text-caption font-medium text-text-tertiary hover:text-text-primary"
                          onClick={() => handleSort("signal_total")}
                        >
                          Total
                          <ArrowUpDown size={12} />
                        </button>
                      </TableHead>
                      <TableHead className="text-right">
                        <button
                          className="flex items-center justify-end gap-1 text-caption font-medium text-text-tertiary hover:text-text-primary"
                          onClick={() => handleSort("signal_suppressed")}
                        >
                          Suppressed
                          <ArrowUpDown size={12} />
                        </button>
                      </TableHead>
                      <TableHead className="text-right">
                        <button
                          className="flex items-center justify-end gap-1 text-caption font-medium text-text-tertiary hover:text-text-primary"
                          onClick={() => handleSort("signal_tasked")}
                        >
                          Tasked
                          <ArrowUpDown size={12} />
                        </button>
                      </TableHead>
                      <TableHead className="text-right">
                        <button
                          className="flex items-center justify-end gap-1 text-caption font-medium text-text-tertiary hover:text-text-primary"
                          onClick={() => handleSort("false_positive_rate")}
                        >
                          FP Rate
                          <ArrowUpDown size={12} />
                        </button>
                      </TableHead>
                      <TableHead className="text-right">
                        <button
                          className="flex items-center justify-end gap-1 text-caption font-medium text-text-tertiary hover:text-text-primary"
                          onClick={() => handleSort("noise_ratio")}
                        >
                          Noise
                          <ArrowUpDown size={12} />
                        </button>
                      </TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {sortedScanners.map((s) => (
                      <TableRow key={s.scanner}>
                        <TableCell className="font-mono text-body-sm text-text-secondary">{s.scanner}</TableCell>
                        <TableCell className="text-right font-mono tabular-nums text-body-sm text-text-primary">
                          {s.signal_total}
                        </TableCell>
                        <TableCell className="text-right font-mono tabular-nums text-body-sm text-text-tertiary">
                          {s.signal_suppressed}
                        </TableCell>
                        <TableCell className="text-right font-mono tabular-nums text-body-sm text-text-tertiary">
                          {s.signal_tasked}
                        </TableCell>
                        <TableCell className="text-right font-mono tabular-nums text-body-sm text-text-tertiary">
                          {Math.round(s.false_positive_rate * 100)}%
                        </TableCell>
                        <TableCell className="text-right font-mono tabular-nums text-body-sm text-text-tertiary">
                          {Math.round(s.noise_ratio * 100)}%
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </FadeIn>
  );
}

type ScannerMetric = {
  scanner: string;
  signal_total: number;
  signal_suppressed: number;
  signal_tasked: number;
  false_positive_rate: number;
  noise_ratio: number;
};

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
