import { cn } from "@/lib/utils";
import { Skeleton } from "@/components/ui/skeleton";

interface SkeletonRowProps {
  columns?: number;
  rows?: number;
  className?: string;
}

export function SkeletonRow({ columns = 5, rows = 5, className }: SkeletonRowProps) {
  return (
    <div className={cn("space-y-2", className)}>
      {Array.from({ length: rows }, (_, i) => (
        <div
          key={i}
          className="flex items-center gap-3 rounded-lg border border-border-default bg-bg-surface px-4 py-3"
        >
          {Array.from({ length: columns }, (_, j) => (
            <Skeleton
              key={j}
              className={cn(
                "h-4 rounded",
                j === 0 ? "w-48" : j === columns - 1 ? "ml-auto w-16" : "w-20",
              )}
            />
          ))}
        </div>
      ))}
    </div>
  );
}
