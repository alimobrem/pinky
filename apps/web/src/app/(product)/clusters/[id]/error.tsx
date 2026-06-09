"use client";

import { ArrowLeft } from "lucide-react";
import { Button } from "@/components/ui/button";
import { RouteErrorBoundary } from "@/components/shared/route-error-boundary";
import Link from "next/link";

export default function ClusterDetailError({
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
      title="Failed to load cluster"
      description="This cluster may have been removed or an error occurred."
      backAction={
        <Button variant="default" size="sm" asChild>
          <Link href="/settings">
            <ArrowLeft size={14} />
            Back to Settings
          </Link>
        </Button>
      }
    />
  );
}
