"use client";

import { ArrowLeft } from "lucide-react";
import { Button } from "@/components/ui/button";
import { RouteErrorBoundary } from "@/components/shared/route-error-boundary";
import Link from "next/link";

export default function TaskDetailError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <RouteErrorBoundary
      error={error}
      reset={reset}
      title="Failed to load task"
      description="This task may have been deleted or an error occurred."
      backAction={
        <Button variant="default" size="sm" asChild>
          <Link href="/tasks">
            <ArrowLeft size={14} />
            Back to Tasks
          </Link>
        </Button>
      }
    />
  );
}
