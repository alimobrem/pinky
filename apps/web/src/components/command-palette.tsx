"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { Search, CheckSquare, Eye, Clock, AlertTriangle, Settings, Brain, Zap } from "lucide-react";

interface CommandItem {
  id: string;
  label: string;
  description?: string;
  icon: React.ReactNode;
  action: () => void;
  category: string;
}

const API = "";

export function CommandPalette() {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [items, setItems] = useState<CommandItem[]>([]);
  const [selected, setSelected] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const dialogRef = useRef<HTMLDivElement>(null);
  const router = useRouter();

  const baseItems: CommandItem[] = [
    { id: "nav-tasks", label: "Tasks", description: "View all tasks", icon: <CheckSquare size={16} />, action: () => router.push("/tasks"), category: "Navigation" },
    { id: "nav-watch", label: "Watch", description: "Live cluster monitoring", icon: <Eye size={16} />, action: () => router.push("/watch"), category: "Navigation" },
    { id: "nav-history", label: "History", description: "Operational history", icon: <Clock size={16} />, action: () => router.push("/history"), category: "Navigation" },
    { id: "nav-alerts", label: "Alerts", description: "Raw signals", icon: <AlertTriangle size={16} />, action: () => router.push("/alerts"), category: "Navigation" },
    { id: "nav-settings", label: "Settings", description: "Platform configuration", icon: <Settings size={16} />, action: () => router.push("/settings"), category: "Navigation" },
  ];

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setOpen(o => !o);
      }
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

      fetch(`${API}/api/v1/work-items?limit=10`)
        .then(r => r.json())
        .then(data => {
          const taskItems: CommandItem[] = (data.items || []).map((wi: any) => ({
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
  }, [open]);

  const filtered = items.filter(item =>
    item.label.toLowerCase().includes(query.toLowerCase()) ||
    (item.description || "").toLowerCase().includes(query.toLowerCase())
  );

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setSelected(s => Math.min(s + 1, filtered.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setSelected(s => Math.max(s - 1, 0));
    } else if (e.key === "Enter" && filtered[selected]) {
      filtered[selected].action();
      setOpen(false);
    }
  };

  if (!open) return null;

  const categories = [...new Set(filtered.map(i => i.category))];

  return (
    <div role="dialog" aria-modal="true" aria-label="Command palette" style={{
      position: "fixed", inset: 0, zIndex: 100,
      background: "rgba(0,0,0,0.6)", backdropFilter: "blur(4px)",
      display: "flex", alignItems: "flex-start", justifyContent: "center",
      paddingTop: 120,
    }} onClick={() => setOpen(false)}>
      <div ref={dialogRef} onClick={e => e.stopPropagation()} onKeyDown={e => {
        if (e.key !== "Tab" || !dialogRef.current) return;
        const focusable = dialogRef.current.querySelectorAll<HTMLElement>("input, button, [tabindex]:not([tabindex='-1'])");
        if (!focusable.length) return;
        const first = focusable[0], last = focusable[focusable.length - 1];
        if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
        else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
      }} style={{
        width: 560, maxHeight: 480,
        background: "var(--bg-elevated)", border: "1px solid var(--border-default)",
        borderRadius: "var(--radius-xl)", boxShadow: "var(--shadow-dropdown)",
        overflow: "hidden", display: "flex", flexDirection: "column",
      }}>
        {/* Search input */}
        <div style={{
          display: "flex", alignItems: "center", gap: "var(--space-3)",
          padding: "var(--space-4)", borderBottom: "1px solid var(--border-subtle)",
        }}>
          <Search size={18} style={{ color: "var(--text-tertiary)", flexShrink: 0 }} />
          <input
            ref={inputRef}
            value={query}
            onChange={e => { setQuery(e.target.value); setSelected(0); }}
            onKeyDown={handleKeyDown}
            placeholder="Search tasks, navigate, run actions..."
            style={{
              flex: 1, background: "none", border: "none", outline: "none",
              color: "var(--text-primary)", fontSize: 15,
              fontFamily: "var(--font-sans)",
            }}
          />
          <kbd style={{
            background: "var(--bg-active)", borderRadius: "var(--radius-sm)",
            padding: "2px 6px", fontSize: 11, color: "var(--text-tertiary)",
          }}>ESC</kbd>
        </div>

        {/* Results */}
        <div style={{ overflowY: "auto", maxHeight: 380 }}>
          {filtered.length === 0 && (
            <div style={{ padding: "var(--space-8)", textAlign: "center", color: "var(--text-tertiary)", fontSize: 13 }}>
              No results for "{query}"
            </div>
          )}

          {categories.map(cat => (
            <div key={cat}>
              <div style={{
                padding: "var(--space-2) var(--space-4)",
                fontSize: 11, fontWeight: 600, color: "var(--text-tertiary)",
                textTransform: "uppercase", letterSpacing: "0.06em",
              }}>{cat}</div>
              {filtered.filter(i => i.category === cat).map((item, i) => {
                const globalIndex = filtered.indexOf(item);
                return (
                  <div
                    key={item.id}
                    onClick={() => { item.action(); setOpen(false); }}
                    style={{
                      display: "flex", alignItems: "center", gap: "var(--space-3)",
                      padding: "var(--space-2) var(--space-4)",
                      cursor: "pointer",
                      background: globalIndex === selected ? "var(--bg-hover)" : "transparent",
                      transition: "background var(--transition-fast)",
                    }}
                  >
                    <span style={{ color: globalIndex === selected ? "var(--accent-brand)" : "var(--text-tertiary)" }}>{item.icon}</span>
                    <div style={{ flex: 1 }}>
                      <div style={{ fontSize: 14, fontWeight: 500 }}>{item.label}</div>
                      {item.description && <div style={{ fontSize: 12, color: "var(--text-tertiary)" }}>{item.description}</div>}
                    </div>
                  </div>
                );
              })}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
