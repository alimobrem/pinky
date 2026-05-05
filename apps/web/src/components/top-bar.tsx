"use client";

import { useSearchParams, useRouter, usePathname } from "next/navigation";
import Link from "next/link";
import { Search, Brain, ChevronDown, LogOut } from "lucide-react";
import { useQuery, useMutation } from "@tanstack/react-query";
import type { ClusterRegistryEntry, PaginatedResponse } from "@pinky/contracts";
import { Breadcrumb, BreadcrumbItem, BreadcrumbLink, BreadcrumbList, BreadcrumbPage, BreadcrumbSeparator } from "@/components/ui/breadcrumb";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";

interface SessionInfo { authenticated: boolean; principal?: { display_name?: string }; }

const PAGE_NAMES: Record<string, string> = {
  dashboard: "Dashboard",
  tasks: "Tasks",
  watch: "Watch",
  history: "History",
  alerts: "Alerts",
  settings: "Settings",
};

export function TopBar() {
  const searchParams = useSearchParams();
  const pathname = usePathname();
  const router = useRouter();
  const selectedCluster = searchParams.get("cluster") || "all";

  const { data: clustersData } = useQuery({
    queryKey: ["clusters"],
    queryFn: () => api.get<PaginatedResponse<ClusterRegistryEntry>>("/api/v1/clusters"),
    staleTime: 60_000,
  });
  const clusters = clustersData?.items ?? [];

  const { data: session } = useQuery({
    queryKey: ["session"],
    queryFn: () => api.get<SessionInfo>("/api/v1/auth/session"),
    staleTime: 30_000,
    refetchInterval: 60_000,
    retry: false,
  });

  const logoutMutation = useMutation({
    mutationFn: () => api.post("/api/v1/auth/logout"),
    onSuccess: () => { window.location.href = "/login"; },
  });

  const handleClusterChange = (value: string) => {
    const params = new URLSearchParams(searchParams.toString());
    if (value === "all") params.delete("cluster");
    else params.set("cluster", value);
    const qs = params.toString();
    router.replace(qs ? `${pathname}?${qs}` : pathname);
  };

  const segments = pathname.split("/").filter(Boolean);
  const breadcrumbs = segments.map((seg, i) => ({
    label: PAGE_NAMES[seg] || (seg.length > 12 ? `${seg.slice(0, 8)}...` : seg),
    href: "/" + segments.slice(0, i + 1).join("/"),
    isLast: i === segments.length - 1,
  }));

  return (
    <header className="border-b border-border-subtle bg-bg-primary/95 backdrop-blur supports-[backdrop-filter]:bg-bg-primary/90">
      <div className="flex flex-col gap-3 px-4 py-3 lg:px-5 min-[1440px]:flex-row min-[1440px]:items-center min-[1440px]:justify-between">
        <div className="flex min-w-0 flex-col gap-3 lg:flex-row lg:flex-wrap lg:items-center lg:gap-4 min-[1440px]:flex-nowrap">
          {breadcrumbs.length > 0 && (
            <Breadcrumb>
              <BreadcrumbList>
                {breadcrumbs.map((bc, i) => (
                  <BreadcrumbItem key={bc.href}>
                    {i > 0 && <BreadcrumbSeparator />}
                    {bc.isLast ? (
                      <BreadcrumbPage>{bc.label}</BreadcrumbPage>
                    ) : (
                      <BreadcrumbLink asChild>
                        <Link href={bc.href}>{bc.label}</Link>
                      </BreadcrumbLink>
                    )}
                  </BreadcrumbItem>
                ))}
              </BreadcrumbList>
            </Breadcrumb>
          )}

          <div className="hidden h-4 w-px bg-border-subtle lg:block" />

          <div className="flex min-w-0 flex-col gap-2 sm:flex-row sm:flex-wrap sm:items-center">
            <Select value={selectedCluster} onValueChange={handleClusterChange}>
              <SelectTrigger className="w-full sm:w-[200px] h-9 text-xs" aria-label="Cluster selector">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Clusters ({clusters.length})</SelectItem>
                {clusters.map(c => <SelectItem key={c.id} value={c.id}>{c.display_name}</SelectItem>)}
              </SelectContent>
            </Select>

            <Button
              variant="outline"
              size="sm"
              onClick={() => window.dispatchEvent(new KeyboardEvent("keydown", { key: "k", metaKey: true }))}
              className="justify-start gap-2 text-text-tertiary sm:min-w-[220px]"
            >
              <Search size={13} />
              <span>Search...</span>
              <kbd className="ml-auto rounded border border-border-default bg-bg-active px-1.5 py-0.5 font-mono text-xs text-text-tertiary">⌘K</kbd>
            </Button>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-3 text-xs sm:gap-5 min-[1440px]:justify-end">
          <div className="flex items-center gap-2 text-text-tertiary">
            <Brain size={13} className="text-accent-brain" />
            <span className="h-1.5 w-1.5 rounded-full bg-status-done animate-brain-pulse" />
            <span className="font-medium">Brain active</span>
          </div>
          {session?.authenticated ? (
            <div className="flex items-center gap-3">
              <div className="flex items-center gap-2 font-medium text-text-secondary">
                <span className="h-1.5 w-1.5 rounded-full bg-status-done" />
                <span>{session.principal?.display_name || "Connected"}</span>
              </div>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => logoutMutation.mutate()}
                title="Sign out"
                className="h-7 w-7 p-0 text-text-tertiary hover:text-text-secondary"
              >
                <LogOut size={13} />
              </Button>
            </div>
          ) : session !== undefined ? (
            <Link href="/login" className={cn("flex items-center gap-2 no-underline font-medium", "text-status-blocked")}>
              <span className="h-1.5 w-1.5 rounded-full bg-status-blocked" />
              <span>Session expired</span>
            </Link>
          ) : null}
        </div>
      </div>
    </header>
  );
}
