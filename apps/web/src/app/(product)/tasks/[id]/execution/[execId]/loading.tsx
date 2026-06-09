import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

export default function ExecutionDetailLoading() {
  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <Skeleton className="h-8 w-8 rounded-md" />
        <div className="flex-1">
          <Skeleton className="h-7 w-48" />
          <div className="mt-2">
            <Skeleton className="h-5 w-20 rounded-full" />
          </div>
        </div>
      </div>

      <Card className="overflow-hidden p-4">
        <div className="space-y-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="flex items-start gap-3 rounded-md px-2 py-1.5">
              <Skeleton className="mt-1 h-3.5 w-3.5 rounded-full" />
              <Skeleton className="h-4 w-3/4" />
              <Skeleton className="ml-auto h-3 w-16" />
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}
