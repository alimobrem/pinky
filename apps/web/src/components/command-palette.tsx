"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { Search, CheckSquare, Eye, Clock, AlertTriangle, Settings, Brain } from "lucide-react";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";

interface CommandItem {
  id: string;
  label: string;
  description?: string;
  icon: React.ReactNode;
  action: () => void;
  category: string;
}

export function CommandPalette() {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [items, setItems] = useState<CommandItem[]>([]);
  const [selected, setSelected] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const dialogRef = useRef<HTMLDivElement>(null);
  const router = useRouter();

  const baseItems = useMemo<CommandItem[]>(() => [
    { id: "nav-tasks", label: "Tasks", description: "View all tasks", icon: <CheckSquare size={16} />, action: () => router.push("/tasks"), category: "Navigation" },
    { id: "nav-watch", label: "Watch", description: "Live cluster monitoring", icon: <Eye size={16} />, action: () => router.push("/watch"), category: "Navigation" },
    { id: "nav-history", label: "History", description: "Operational history", icon: <Clock size={16} />, action: () => router.push("/history"), category: "Navigation" },
    { id: "nav-alerts", label: "Alerts", description: "Raw signals", icon: <AlertTriangle size={16} />, action: () => router.push("/alerts"), category: "Navigation" },
    { id: "nav-settings", label: "Settings", description: "Platform configuration", icon: <Settings size={16} />, action: () => router.push("/settings"), category: "Navigation" },
  ], [router]);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") { e.preventDefault(); setOpen(o => !o); }
      if (e.key === "Escape") setOpen(false);
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, []);

  useEffect(() => {
    if (open) {
      inputRef.current?.focus();
      setQuery("");
      setSelected(0);
      api.get<{ items: Record<string, string>[] }>("/api/v1/work-items?limit=10")
        .then(data => {
          const taskItems: CommandItem[] = (data.items || []).map((wi: Record<string, string>) => ({
            id: `task-${wi.id}`,
            label: wi.title,
            description: `${wi.status} · ${wi.priority}`,
            icon: <Brain size={16} />,
            action: () => router.push(`/tasks/${wi.id}`),
            category: "Tasks",
          }));
          setItems([...baseItems, ...taskItems]);
        })
        .catch(() => setItems(baseItems));
    }
  }, [open, baseItems, router]);

  const filtered = items.filter(item =>
    item.label.toLowerCase().includes(query.toLowerCase()) ||
    (item.description || "").toLowerCase().includes(query.toLowerCase())
  );

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "ArrowDown") { e.preventDefault(); setSelected(s => Math.min(s + 1, filtered.length - 1)); }
    else if (e.key === "ArrowUp") { e.preventDefault(); setSelected(s => Math.max(s - 1, 0)); }
    else if (e.key === "Enter" && filtered[selected]) { filtered[selected].action(); setOpen(false); }
  };

  if (!open) return null;

  const categories = [...new Set(filtered.map(i => i.category))];

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Command palette"
      className="fixed inset-0 z-100 bg-black/60 backdrop-blur-sm flex items-start justify-center pt-[120px]"
      onClick={() => setOpen(false)}
    >
      <div
        ref={dialogRef}
        onClick={e => e.stopPropagation()}
        onKeyDown={e => {
          if (e.key !== "Tab" || !dialogRef.current) return;
          const focusable = dialogRef.current.querySelectorAll<HTMLElement>("input, button, [tabindex]:not([tabindex='-1'])");
          if (!focusable.length) return;
          const first = focusable[0], last = focusable[focusable.length - 1];
          if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
          else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
        }}
        className="w-[560px] max-h-[480px] bg-bg-elevated border border-border-default rounded-xl shadow-dropdown overflow-hidden flex flex-col"
      >
        <div className="flex items-center gap-3 p-4 border-b border-border-subtle">
          <Search size={18} className="text-text-tertiary shrink-0" />
          <input
            ref={inputRef}
            value={query}
            onChange={e => { setQuery(e.target.value); setSelected(0); }}
            onKeyDown={handleKeyDown}
            placeholder="Search tasks, navigate, run actions..."
            className="flex-1 bg-transparent border-none outline-none text-text-primary text-[15px] font-sans"
          />
          <kbd className="bg-bg-active rounded-sm px-1.5 py-0.5 text-[11px] text-text-tertiary">ESC</kbd>
        </div>

        <div className="overflow-y-auto max-h-[380px]" role="listbox" aria-label="Command palette results">
          {filtered.length === 0 && (
            <div className="p-8 text-center text-text-tertiary text-sm">
              No results for &quot;{query}&quot;
            </div>
          )}

          {categories.map(cat => (
            <div key={cat}>
              <div className="px-4 py-2 text-[11px] font-semibold text-text-tertiary uppercase tracking-wider">{cat}</div>
              {filtered.filter(i => i.category === cat).map(item => {
                const globalIndex = filtered.indexOf(item);
                return (
                  <button
                    key={item.id}
                    onClick={() => { item.action(); setOpen(false); }}
                    type="button"
                    role="option"
                    aria-selected={globalIndex === selected}
                    className={cn(
                      "w-full text-left flex items-center gap-3 px-4 py-2 cursor-pointer transition-colors",
                      globalIndex === selected ? "bg-bg-hover" : "bg-transparent"
                    )}
                  >
                    <span className={globalIndex === selected ? "text-accent-brand" : "text-text-tertiary"}>{item.icon}</span>
                    <div className="flex-1">
                      <div className="text-sm font-medium">{item.label}</div>
                      {item.description && <div className="text-xs text-text-tertiary">{item.description}</div>}
                    </div>
                  </button>
                );
              })}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
