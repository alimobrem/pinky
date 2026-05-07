export interface SkeletonProps {
  width?: string;
  height?: string;
}

export function Skeleton({ width = "100%", height = "1rem" }: SkeletonProps) {
  return (
    <div
      className="rounded bg-[var(--bg-elevated,#e5e7eb)]"
      style={{ width, height }}
    />
  );
}
