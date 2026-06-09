import { Skeleton } from "@/components/ui/skeleton";

export default function HistoryLoading() {
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <Skeleton className="h-7 w-24" />
          <Skeleton className="mt-2 h-4 w-44" />
        </div>
        <Skeleton className="h-9 w-24" />
      </div>

      <div className="flex items-center gap-3">
        <Skeleton className="h-9 w-48" />
        <Skeleton className="h-7 w-28" />
        <Skeleton className="h-7 w-16" />
      </div>

      <div className="rounded-lg border border-border-default">
        <div className="flex items-center gap-4 border-b border-border-default px-4 py-2">
          <Skeleton className="h-3 w-20" />
          <Skeleton className="h-3 w-24" />
          <Skeleton className="h-3 w-16" />
          <Skeleton className="h-3 w-20" />
          <Skeleton className="h-3 w-16" />
          <Skeleton className="h-3 w-6" />
        </div>
        {Array.from({ length: 8 }).map((_, i) => (
          <div
            key={i}
            className="flex items-center gap-4 border-b border-border-default px-4 py-3 last:border-b-0"
          >
            <Skeleton className="h-3 w-20" />
            <div className="flex items-center gap-1.5">
              <Skeleton className="h-2 w-2 rounded-full" />
              <Skeleton className="h-4 w-32" />
            </div>
            <Skeleton className="h-3 w-16" />
            <Skeleton className="h-3 w-20" />
            <Skeleton className="h-3 w-16" />
            <Skeleton className="h-3 w-4" />
          </div>
        ))}
      </div>
    </div>
  );
}
