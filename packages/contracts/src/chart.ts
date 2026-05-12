export interface ChartSeries {
  key: string;
  label: string;
  color: string;
}

export interface ChartData {
  type: "bar" | "line";
  title: string;
  xKey: string;
  data: Record<string, string | number>[];
  series: ChartSeries[];
}
