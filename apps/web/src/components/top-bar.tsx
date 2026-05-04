"use client";

import { useEffect, useState } from "react";
import { useSearchParams, useRouter, usePathname } from "next/navigation";
import Link from "next/link";
import { Search, Brain, ChevronDown, LogOut } from "lucide-react";
import { Breadcrumb, BreadcrumbItem, BreadcrumbLink, BreadcrumbList, BreadcrumbPage, BreadcrumbSeparator } from "@/components/ui/breadcrumb";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";

interface Cluster { id: string; display_name: string; onboarding_state: string; }
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
  const [clusters, setClusters] = useState<Cluster[]>([]);
  const [session, setSession] = useState<SessionInfo | null>(null);
  const searchParams = useSearchParams();
  const pathname = usePathname();
  const router = useRouter();
  const selectedCluster = searchParams.get("cluster") || "all";

  useEffect(() => {
    api.get<{ items: Cluster[] }>("/api/v1/clusters")
      .then(d => setClusters(d.items || []))
      .catch(() => setClusters([]));
  }, []);

  useEffect(() => {
    const checkSession = () =>
      fetch("/api/v1/auth/session", { credentials: "include" })
        .then(r => r.json())
        .then(setSession)
        .catch(() => setSession({ authenticated: false }));
    checkSession();
    const interval = setInterval(checkSession, 60000);
    return () => clearInterval(interval);
  }, []);

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
            <div className="relative sm:min-w-[180px]">
              <select
                aria-label="Cluster selector"
                value={selectedCluster}
                onChange={e => handleClusterChange(e.target.value)}
                className="w-full appearance-none rounded-lg border border-border-default bg-bg-surface py-2 pl-3 pr-8 text-xs font-medium text-text-primary transition-colors hover:border-accent-brain/30 focus:outline-none focus:ring-1 focus:ring-ring sm:w-auto"
              >
                <option value="all">All Clusters ({clusters.length})</option>
                {clusters.map(c => <option key={c.id} value={c.id}>{c.display_name}</option>)}
              </select>
              <ChevronDown size={12} className="pointer-events-none absolute right-2.5 top-1/2 -translate-y-1/2 text-text-tertiary" />
            </div>

            <button
              onClick={() => window.dispatchEvent(new KeyboardEvent("keydown", { key: "k", metaKey: true }))}
              className="flex w-full items-center gap-2 rounded-lg border border-border-default bg-bg-surface px-3 py-2 text-xs text-text-tertiary transition-colors hover:border-accent-brain/30 sm:w-auto sm:min-w-[220px]"
            >
              <Search size={13} />
              <span>Search...</span>
              <kbd className="ml-auto rounded border border-border-default bg-bg-active px-1.5 py-0.5 font-mono text-xs text-text-tertiary sm:ml-4">⌘K</kbd>
            </button>
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
              <button
                onClick={async () => {
                  await fetch("/api/v1/auth/logout", { method: "POST", credentials: "include" });
                  window.location.href = "/login";
                }}
                className="cursor-pointer border-none bg-transparent p-1 text-text-tertiary transition-colors hover:text-text-secondary"
                title="Sign out"
              >
                <LogOut size={13} />
              </button>
            </div>
          ) : session !== null ? (
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
