"use client";

import { ArrowLeft } from "lucide-react";
import { Button } from "@/components/ui/button";
import { RouteErrorBoundary } from "@/components/shared/route-error-boundary";

export default function ExecutionDetailError({
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
      title="Failed to load execution"
      description="This execution may have been deleted or an error occurred."
      backAction={
        <Button
          variant="default"
          size="sm"
          onClick={() => window.history.back()}
        >
          <ArrowLeft size={14} />
          Go Back
        </Button>
      }
    />
  );
}
