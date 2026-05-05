"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import {
  LayoutDashboard,
  ListTodo,
  Eye,
  Clock,
  Bell,
  Settings,
  Search,
  ArrowRight,
} from "lucide-react";
import type { WorkItem, Issue, PaginatedResponse, ClusterRegistryEntry } from "@pinky/contracts";
import { api } from "@/lib/api";
import { QUERY_KEYS } from "@/lib/constants";
import { useCommandActions } from "@/components/command-palette/command-context";
import {
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
  CommandSeparator,
} from "@/components/ui/command";
import { Kbd } from "@/components/shared/keyboard-shortcut-hint";

export function CommandPalette() {
  const [open, setOpen] = useState(false);
  const router = useRouter();
  const { actions } = useCommandActions();

  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setOpen((prev) => !prev);
      }
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  const { data: tasks } = useQuery({
    queryKey: [...QUERY_KEYS.tasks(), "cmd-palette"],
    queryFn: () =>
      api.get<PaginatedResponse<WorkItem>>("/api/v1/work-items?limit=10"),
    enabled: open,
    staleTime: 10_000,
  });

  const { data: issues } = useQuery({
    queryKey: [...QUERY_KEYS.issues(), "cmd-palette"],
    queryFn: () =>
      api.get<PaginatedResponse<Issue>>("/api/v1/issues?status=open&limit=5"),
    enabled: open,
    staleTime: 10_000,
  });

  const { data: clusters } = useQuery({
    queryKey: QUERY_KEYS.clusters(),
    queryFn: () =>
      api.get<PaginatedResponse<ClusterRegistryEntry>>("/api/v1/clusters"),
    enabled: open,
    staleTime: 60_000,
  });

  function navigate(path: string) {
    setOpen(false);
    router.push(path);
  }

  const pages = [
    { label: "Dashboard", path: "/dashboard", icon: LayoutDashboard, shortcut: "G D" },
    { label: "Tasks", path: "/tasks", icon: ListTodo, shortcut: "G T" },
    { label: "Watch", path: "/watch", icon: Eye, shortcut: "G W" },
    { label: "History", path: "/history", icon: Clock, shortcut: "G H" },
    { label: "Alerts", path: "/alerts", icon: Bell, shortcut: "G A" },
    { label: "Settings", path: "/settings", icon: Settings, shortcut: "G S" },
  ];

  return (
    <CommandDialog open={open} onOpenChange={setOpen}>
      <CommandInput placeholder="Search tasks, issues, clusters, or navigate..." />
      <CommandList>
        <CommandEmpty>
          <div className="flex flex-col items-center gap-2 py-6">
            <Search size={20} className="text-text-tertiary" />
            <p className="text-sm text-text-secondary">No results found</p>
          </div>
        </CommandEmpty>

        {actions.length > 0 && (
          <>
            <CommandGroup heading="Actions">
              {actions.map((action) => (
                <CommandItem
                  key={action.id}
                  onSelect={() => {
                    action.onSelect();
                    setOpen(false);
                  }}
                >
                  {action.icon}
                  <span>{action.label}</span>
                  {action.shortcut && (
                    <Kbd keys={action.shortcut} className="ml-auto" />
                  )}
                </CommandItem>
              ))}
            </CommandGroup>
            <CommandSeparator />
          </>
        )}

        <CommandGroup heading="Navigation">
          {pages.map((page) => (
            <CommandItem key={page.path} onSelect={() => navigate(page.path)}>
              <page.icon size={16} className="mr-2 text-text-tertiary" />
              <span>{page.label}</span>
              <Kbd keys={page.shortcut} className="ml-auto" />
            </CommandItem>
          ))}
        </CommandGroup>

        {tasks?.items && tasks.items.length > 0 && (
          <>
            <CommandSeparator />
            <CommandGroup heading="Tasks">
              {tasks.items.map((task) => (
                <CommandItem
                  key={task.id}
                  onSelect={() => navigate(`/tasks/${task.id}`)}
                >
                  <ListTodo size={14} className="mr-2 shrink-0 text-text-tertiary" />
                  <span className="truncate">{task.title}</span>
                  <ArrowRight size={12} className="ml-auto shrink-0 text-text-tertiary" />
                </CommandItem>
              ))}
            </CommandGroup>
          </>
        )}

        {issues?.items && issues.items.length > 0 && (
          <>
            <CommandSeparator />
            <CommandGroup heading="Open Issues">
              {issues.items.map((issue) => (
                <CommandItem
                  key={issue.id}
                  onSelect={() => navigate(`/watch?issue=${issue.id}`)}
                >
                  <Eye size={14} className="mr-2 shrink-0 text-text-tertiary" />
                  <span className="truncate">{issue.title}</span>
                </CommandItem>
              ))}
            </CommandGroup>
          </>
        )}

        {clusters?.items && clusters.items.length > 0 && (
          <>
            <CommandSeparator />
            <CommandGroup heading="Clusters">
              {clusters.items.map((cluster) => (
                <CommandItem
                  key={cluster.id}
                  onSelect={() => navigate(`/tasks?cluster=${cluster.id}`)}
                >
                  <span className="truncate">{cluster.display_name}</span>
                </CommandItem>
              ))}
            </CommandGroup>
          </>
        )}
      </CommandList>
    </CommandDialog>
  );
}
