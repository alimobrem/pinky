"use client";

import { LayoutDashboard } from "lucide-react";
import { Button } from "@/components/ui/button";
import { RouteErrorBoundary } from "@/components/shared/route-error-boundary";

export default function ProductError({
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
      title="Something went wrong"
      description="An unexpected error occurred. You can retry or navigate away."
      backAction={
        <Button
          variant="default"
          size="sm"
          onClick={() => (window.location.href = "/dashboard")}
        >
          <LayoutDashboard size={14} />
          Dashboard
        </Button>
      }
    />
  );
}
