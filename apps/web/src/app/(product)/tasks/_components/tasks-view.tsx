"use client";

import { useState, useMemo, useCallback } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import type { WorkItem } from "@pinky/contracts";
import { cn } from "@/lib/utils";
import { tasksOptions, clustersOptions } from "../queries";
import { taskColumns, TaskRowCard } from "./task-row";
import { TaskPreview } from "./task-preview";
import { DataTable } from "@/components/shared/data-table";
import { SearchFilterBar } from "@/components/shared/search-filter-bar";
import { EmptyState } from "@/components/shared/empty-state";
import { SkeletonRow } from "@/components/shared/skeleton-row";
import { PageHeader } from "@/components/shared/page-header";
import { useCluster } from "@/hooks/use-cluster";
import { useIsDesktop } from "@/hooks/use-media-query";
import { useSSE } from "@/hooks/use-sse";
import { QUERY_KEYS } from "@/lib/constants";
import { FadeIn } from "@/components/motion/fade-in";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { ListTodo } from "lucide-react";

const QUEUE_TABS = [
  { id: "all", label: "All" },
  { id: "ready", label: "Ready" },
  { id: "active", label: "Active" },
  { id: "blocked", label: "Blocked" },
  { id: "waiting_for_approval", label: "Approval" },
] as const;

export function TasksView() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const clusterId = useCluster();
  const isDesktop = useIsDesktop();
  const qc = useQueryClient();

  useSSE("/api/v1/streams/events", {
    onEvent: {
      update: () => qc.invalidateQueries({ queryKey: QUERY_KEYS.tasks() }),
    },
  });

  const [activeTab, setActiveTab] = useState(searchParams.get("status") ?? "all");
  const [search, setSearch] = useState("");
  const [priorityFilter, setPriorityFilter] = useState("all");
  const [focusedId, setFocusedId] = useState<string | null>(null);

  const { data: tasks, isLoading } = useQuery(
    tasksOptions({
      cluster_id: clusterId ?? undefined,
    }),
  );
  const { data: clusters } = useQuery(clustersOptions());

  const clusterMap = useMemo(() => {
    const map: Record<string, string> = {};
    for (const c of clusters?.items ?? []) {
      map[c.id] = c.display_name;
    }
    return map;
  }, [clusters]);

  const filteredItems = useMemo(() => {
    let items = tasks?.items ?? [];

    if (activeTab === "active") {
      items = items.filter((t) =>
        ["accepted", "in_progress"].includes(t.status),
      );
    } else if (activeTab !== "all") {
      items = items.filter((t) => t.status === activeTab);
    }

    if (priorityFilter !== "all") {
      items = items.filter((t) => t.priority === priorityFilter);
    }

    if (search) {
      const q = search.toLowerCase();
      items = items.filter(
        (t) =>
          t.title.toLowerCase().includes(q) ||
          t.why_now?.toLowerCase().includes(q),
      );
    }

    return items;
  }, [tasks, activeTab, priorityFilter, search]);

  const tabCounts = useMemo(() => {
    const items = tasks?.items ?? [];
    return {
      all: items.length,
      ready: items.filter((t) => t.status === "ready").length,
      active: items.filter((t) =>
        ["accepted", "in_progress"].includes(t.status),
      ).length,
      blocked: items.filter((t) => t.status === "blocked").length,
      waiting_for_approval: items.filter(
        (t) => t.status === "waiting_for_approval",
      ).length,
    };
  }, [tasks]);

  const focusedTask = useMemo(
    () => filteredItems.find((t) => t.id === focusedId) ?? null,
    [filteredItems, focusedId],
  );

  const handleRowClick = useCallback(
    (task: WorkItem) => {
      router.push(`/tasks/${task.id}`);
    },
    [router],
  );

  const columns = useMemo(() => taskColumns(clusterMap), [clusterMap]);

  return (
    <div className="space-y-4">
      <PageHeader
        title="Tasks"
        description="Work items surfaced by The Brain across your fleet"
        meta={
          <span className="font-mono tabular-nums">{tasks?.total_count ?? 0} total</span>
        }
      />

      <div className="flex items-center gap-1 border-b border-border-default">
        {QUEUE_TABS.map((tab) => {
          const count = tabCounts[tab.id as keyof typeof tabCounts] ?? 0;
          return (
            <button
              key={tab.id}
              type="button"
              onClick={() => setActiveTab(tab.id)}
              className={cn(
                "relative flex items-center gap-1.5 border-b-2 px-3 py-2 text-body-sm font-medium transition-colors",
                activeTab === tab.id
                  ? "border-brand-pink text-text-primary"
                  : "border-transparent text-text-tertiary hover:text-text-secondary",
              )}
            >
              {tab.label}
              <span
                className={cn(
                  "min-w-5 rounded-md px-1.5 py-0.5 text-center font-mono text-[10px] tabular-nums",
                  activeTab === tab.id
                    ? "bg-brand-pink/15 text-brand-pink"
                    : "bg-bg-hover text-text-tertiary",
                )}
              >
                {count}
              </span>
            </button>
          );
        })}
      </div>

      <SearchFilterBar
        value={search}
        onChange={setSearch}
        placeholder="Search tasks..."
        filters={
          <Select value={priorityFilter} onValueChange={setPriorityFilter}>
            <SelectTrigger className="h-7 w-auto min-w-[100px] border-0 bg-transparent text-xs shadow-none">
              <SelectValue placeholder="Priority" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All priorities</SelectItem>
              <SelectItem value="critical">Critical</SelectItem>
              <SelectItem value="high">High</SelectItem>
              <SelectItem value="medium">Medium</SelectItem>
              <SelectItem value="low">Low</SelectItem>
            </SelectContent>
          </Select>
        }
      />

      {isLoading ? (
        <SkeletonRow rows={8} />
      ) : (
        <FadeIn>
          <div className="flex gap-4">
            <div className={cn("min-w-0", isDesktop ? "flex-1" : "w-full")}>
              {isDesktop ? (
                <DataTable
                  data={filteredItems}
                  columns={columns}
                  keyFn={(t) => t.id}
                  onRowClick={handleRowClick}
                  focusedKey={focusedId}
                  onFocusChange={setFocusedId}
                  stickyHeader
                  emptyState={
                    <EmptyState
                      icon={ListTodo}
                      title="No tasks match your filters"
                      description="Try adjusting your search or filter criteria"
                    />
                  }
                />
              ) : (
                <div className="space-y-2">
                  {filteredItems.length === 0 ? (
                    <EmptyState
                      icon={ListTodo}
                      title="No tasks match your filters"
                      description="Try adjusting your search or filter criteria"
                    />
                  ) : (
                    filteredItems.map((task) => (
                      <div
                        key={task.id}
                        onClick={() => handleRowClick(task)}
                        className="cursor-pointer"
                      >
                        <TaskRowCard
                          task={task}
                          clusterName={clusterMap[task.cluster_id]}
                        />
                      </div>
                    ))
                  )}
                </div>
              )}
            </div>
            {isDesktop && (
              <div className="w-[300px] shrink-0">
                <TaskPreview
                  task={focusedTask}
                  clusterName={
                    focusedTask ? clusterMap[focusedTask.cluster_id] : undefined
                  }
                />
              </div>
            )}
          </div>
        </FadeIn>
      )}
    </div>
  );
}
