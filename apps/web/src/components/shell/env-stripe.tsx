"use client";

import { cn } from "@/lib/utils";

interface EnvStripeProps {
  environment?: string;
}

const ENV_CLASS: Record<string, string> = {
  production: "bg-env-production",
  staging: "bg-env-staging",
  development: "bg-env-development",
};

export function EnvStripe({ environment }: EnvStripeProps) {
  return (
    <div
      className={cn("h-[3px] w-full shrink-0", ENV_CLASS[environment ?? ""] ?? "bg-env-default")}
      role="status"
      aria-label={`Environment: ${environment ?? "all"}`}
    />
  );
}
