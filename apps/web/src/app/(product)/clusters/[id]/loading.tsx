import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

export default function ClusterDetailLoading() {
  return (
    <div className="space-y-4">
      <Skeleton className="h-4 w-12" />

      <div>
        <Skeleton className="h-7 w-48" />
        <Skeleton className="mt-2 h-4 w-64" />
        <div className="mt-2 flex gap-2">
          <Skeleton className="h-5 w-20 rounded-full" />
          <Skeleton className="h-5 w-28 rounded-full" />
        </div>
      </div>

      <div className="flex gap-2 border-b border-border-default pb-px">
        {Array.from({ length: 5 }).map((_, i) => (
          <Skeleton key={i} className="h-9 w-24" />
        ))}
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        {Array.from({ length: 4 }).map((_, i) => (
          <Card key={i}>
            <CardContent className="flex items-start gap-3 p-4">
              <Skeleton className="h-9 w-9 rounded-lg" />
              <div className="space-y-2">
                <Skeleton className="h-3 w-24" />
                <Skeleton className="h-4 w-40" />
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="flex gap-6">
        <Skeleton className="h-6 w-16" />
        <Skeleton className="h-6 w-24" />
        <Skeleton className="h-6 w-20" />
      </div>
    </div>
  );
}
