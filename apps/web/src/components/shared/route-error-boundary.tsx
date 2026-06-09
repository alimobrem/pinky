"use client";

import { useEffect } from "react";
import { AlertTriangle, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import type { ReactNode } from "react";

interface RouteErrorBoundaryProps {
  error: Error & { digest?: string };
  reset: () => void;
  title: string;
  description: string;
  backAction: ReactNode;
}

export function RouteErrorBoundary({
  error,
  reset,
  title,
  description,
  backAction,
}: RouteErrorBoundaryProps) {
  useEffect(() => {
    console.error("[RouteError]", error);
  }, [error]);

  return (
    <div className="flex items-center justify-center py-24">
      <Card className="max-w-md w-full">
        <CardContent className="flex flex-col items-center gap-4 p-8 text-center">
          <div className="rounded-xl bg-destructive/10 p-4">
            <AlertTriangle size={24} className="text-destructive" />
          </div>
          <div className="space-y-1">
            <p className="text-sm font-medium text-text-primary">{title}</p>
            <p className="text-body-sm text-text-secondary">{description}</p>
          </div>
          <pre className="w-full rounded-md bg-bg-surface p-3 text-left text-caption text-text-tertiary overflow-auto max-h-24">
            {error.message}
          </pre>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" onClick={reset}>
              <RefreshCw size={14} />
              Retry
            </Button>
            {backAction}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
