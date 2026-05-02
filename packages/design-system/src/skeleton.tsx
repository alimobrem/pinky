export interface SkeletonProps {
  width?: string;
  height?: string;
}

export function Skeleton({ width = "100%", height = "1rem" }: SkeletonProps) {
  return <div style={{ width, height, background: "var(--bg-elevated, #e5e7eb)", borderRadius: 4 }} />;
}
