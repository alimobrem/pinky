"use client";

import { useSearchParams } from "next/navigation";

export function useCluster(): string | null {
  const searchParams = useSearchParams();
  const cluster = searchParams.get("cluster");
  if (!cluster || cluster === "all") return null;
  return cluster;
}
