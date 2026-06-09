import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

export default function WatchLoading() {
  return (
    <div className="space-y-4">
      <div>
        <Skeleton className="h-7 w-24" />
        <Skeleton className="mt-2 h-4 w-48" />
      </div>

      <div className="flex gap-2">
        <Skeleton className="h-9 w-24" />
        <Skeleton className="h-9 w-24" />
      </div>

      <div className="grid grid-cols-3 gap-3 sm:grid-cols-6">
        {Array.from({ length: 6 }).map((_, i) => (
          <Card key={i} className="py-3">
            <CardContent className="flex items-center gap-3 px-4 pb-0">
              <Skeleton className="h-5 w-5" />
              <div className="space-y-2">
                <Skeleton className="h-5 w-10" />
                <Skeleton className="h-3 w-16" />
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="flex items-center gap-3">
        <Skeleton className="h-9 w-48" />
        <Skeleton className="h-7 w-24" />
        <Skeleton className="h-7 w-16" />
      </div>

      <div className="space-y-2">
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="flex items-center gap-3 rounded-lg border border-border-default px-4 py-3">
            <Skeleton className="h-4 w-4" />
            <Skeleton className="h-4 w-4" />
            <div className="flex-1 space-y-2">
              <Skeleton className="h-4 w-3/4" />
              <div className="flex gap-2">
                <Skeleton className="h-5 w-16 rounded-full" />
                <Skeleton className="h-5 w-16 rounded-full" />
                <Skeleton className="h-3 w-20" />
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
