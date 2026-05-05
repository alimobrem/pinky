"use client";

import { useQuery, useMutation } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { Search, LogOut, PanelLeft, User } from "lucide-react";
import type { ClusterRegistryEntry, PaginatedResponse } from "@pinky/contracts";
import { cn } from "@/lib/utils";
import { api } from "@/lib/api";
import { QUERY_KEYS } from "@/lib/constants";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Kbd } from "@/components/shared/keyboard-shortcut-hint";
import { useCluster } from "@/hooks/use-cluster";

interface TopBarProps {
  onTogglePanel?: () => void;
  panelOpen?: boolean;
}

export function TopBar({ onTogglePanel, panelOpen }: TopBarProps) {
  const router = useRouter();
  const clusterId = useCluster();

  const { data: clusters } = useQuery({
    queryKey: QUERY_KEYS.clusters(),
    queryFn: () =>
      api.get<PaginatedResponse<ClusterRegistryEntry>>("/api/v1/clusters"),
    staleTime: 60_000,
  });

  const { data: session } = useQuery({
    queryKey: QUERY_KEYS.session(),
    queryFn: () =>
      api.get<{ authenticated: boolean; principal?: { display_name?: string; email?: string } }>(
        "/api/v1/auth/session",
      ),
    staleTime: 120_000,
  });

  const logout = useMutation({
    mutationFn: () => api.post("/api/v1/auth/logout"),
    onSuccess: () => router.push("/login"),
  });

  const clusterList = clusters?.items ?? [];
  const userName = session?.principal?.display_name ?? session?.principal?.email ?? "User";

  function handleClusterChange(value: string) {
    const params = new URLSearchParams(window.location.search);
    if (value === "all") {
      params.delete("cluster");
    } else {
      params.set("cluster", value);
    }
    const qs = params.toString();
    router.push(`${window.location.pathname}${qs ? `?${qs}` : ""}`);
  }

  return (
    <header className="flex h-12 shrink-0 items-center gap-3 border-b border-border-subtle bg-bg-base px-4">
      {onTogglePanel && (
        <Button
          variant="ghost"
          size="icon"
          className="hidden h-7 w-7 text-text-tertiary hover:text-text-secondary xl:flex"
          onClick={onTogglePanel}
          aria-label={panelOpen ? "Close sidebar" : "Open sidebar"}
        >
          <PanelLeft size={16} />
        </Button>
      )}

      <Select value={clusterId ?? "all"} onValueChange={handleClusterChange}>
        <SelectTrigger className="h-7 w-auto min-w-[140px] gap-1.5 border-border-subtle bg-bg-surface text-xs">
          <SelectValue placeholder="All clusters" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all">All clusters</SelectItem>
          {clusterList.map((c) => (
            <SelectItem key={c.id} value={c.id}>
              {c.display_name}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      <button
        type="button"
        className="ml-auto flex h-7 items-center gap-2 rounded-lg border border-border-subtle bg-bg-surface px-3 text-xs text-text-tertiary transition-colors hover:border-border-default hover:text-text-secondary"
        onClick={() => {
          document.dispatchEvent(
            new KeyboardEvent("keydown", { key: "k", metaKey: true }),
          );
        }}
        aria-label="Search"
      >
        <Search size={13} />
        <span className="hidden sm:inline">Search...</span>
        <Kbd keys="cmd+k" className="hidden sm:flex" />
      </button>

      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7 text-text-tertiary hover:text-text-secondary"
          >
            <User size={16} />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" className="w-48">
          <div className="px-2 py-1.5 text-xs text-text-secondary">{userName}</div>
          <DropdownMenuItem
            className="gap-2 text-status-blocked"
            onClick={() => logout.mutate()}
          >
            <LogOut size={14} />
            Sign out
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </header>
  );
}
