"use client";

import { cn } from "@/lib/utils";

interface EnvStripeProps {
  environment?: string;
}

const ENV_CLASS: Record<string, string> = {
  production: "env-stripe-production",
  staging: "env-stripe-staging",
  development: "env-stripe-development",
};

export function EnvStripe({ environment }: EnvStripeProps) {
  const cls = environment ? ENV_CLASS[environment] : undefined;

  return (
    <div
      className={cn("h-[3px] w-full shrink-0", cls ?? "env-stripe-default")}
      role="status"
      aria-label={`Environment: ${environment ?? "all"}`}
    />
  );
}
