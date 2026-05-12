"use client";

import { useMemo } from "react";
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
} from "recharts";
import type { ChartData } from "@pinky/contracts";
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  ChartLegend,
  ChartLegendContent,
  type ChartConfig,
} from "@/components/ui/chart";

interface MetricChartProps {
  chart: ChartData;
}

export function MetricChart({ chart }: MetricChartProps) {
  const config = useMemo<ChartConfig>(() => {
    const cfg: ChartConfig = {};
    for (const s of chart.series) {
      cfg[s.key] = { label: s.label, color: s.color };
    }
    return cfg;
  }, [chart.series]);

  const height = chart.type === "bar"
    ? Math.min(chart.data.length * 28 + 60, 400)
    : 240;

  return (
    <div className="rounded-lg border border-border-default bg-bg-surface p-3">
      <p className="text-caption font-medium text-text-secondary mb-2">
        {chart.title}
      </p>
      {/* eslint-disable react/forbid-component-props -- runtime-computed chart height */}
      <ChartContainer config={config} className="w-full" style={{ height }}>
      {/* eslint-enable react/forbid-component-props */}
        {chart.type === "bar" ? (
          <BarChart accessibilityLayer data={chart.data} layout="vertical" margin={{ left: 8, right: 12, top: 4, bottom: 4 }}>
            <CartesianGrid strokeDasharray="3 3" horizontal={false} />
            <XAxis type="number" axisLine={false} tickLine={false} />
            <YAxis
              type="category"
              dataKey={chart.xKey}
              width={120}
              axisLine={false}
              tickLine={false}
              tickFormatter={(v: string) => v.length > 20 ? `${v.slice(0, 18)}…` : v}
            />
            <ChartTooltip content={<ChartTooltipContent />} />
            <ChartLegend content={<ChartLegendContent />} />
            {chart.series.map((s) => (
              <Bar key={s.key} dataKey={s.key} fill={`var(--color-${s.key})`} radius={[0, 3, 3, 0]} barSize={16} />
            ))}
          </BarChart>
        ) : (
          <LineChart accessibilityLayer data={chart.data} margin={{ left: 8, right: 12, top: 4, bottom: 4 }}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey={chart.xKey} axisLine={false} tickLine={false} />
            <YAxis axisLine={false} tickLine={false} />
            <ChartTooltip content={<ChartTooltipContent />} />
            <ChartLegend content={<ChartLegendContent />} />
            {chart.series.map((s) => (
              <Line key={s.key} dataKey={s.key} stroke={`var(--color-${s.key})`} dot={false} strokeWidth={2} />
            ))}
          </LineChart>
        )}
      </ChartContainer>
    </div>
  );
}
