"use client";

import { useEffect, useState } from "react";
import { X } from "lucide-react";

const SHORTCUTS = [
  { keys: "⌘K", description: "Open command palette" },
  { keys: "j / k", description: "Navigate list items" },
  { keys: "Enter", description: "Open selected item" },
  { keys: "Escape", description: "Close dialog / go back" },
  { keys: "?", description: "Show keyboard shortcuts" },
];

export function KeyboardHelp() {
  const [open, setOpen] = useState(false);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLSelectElement || e.target instanceof HTMLTextAreaElement) return;
      if (e.key === "?" && !e.metaKey && !e.ctrlKey) {
        e.preventDefault();
        setOpen(o => !o);
      }
      if (e.key === "Escape") setOpen(false);
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, []);

  if (!open) return null;

  return (
    <div style={{
      position: "fixed", inset: 0, zIndex: 150,
      background: "rgba(0,0,0,0.6)", backdropFilter: "blur(4px)",
      display: "flex", alignItems: "center", justifyContent: "center",
    }} onClick={() => setOpen(false)}>
      <div onClick={e => e.stopPropagation()} style={{
        width: 400, background: "var(--bg-elevated)", border: "1px solid var(--border-default)",
        borderRadius: "var(--radius-xl)", boxShadow: "var(--shadow-dropdown)",
        padding: "var(--space-6)",
      }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "var(--space-5)" }}>
          <h2 style={{ fontSize: 16, fontWeight: 600 }}>Keyboard Shortcuts</h2>
          <button onClick={() => setOpen(false)} style={{
            background: "none", border: "none", color: "var(--text-tertiary)", cursor: "pointer",
          }}><X size={18} /></button>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-3)" }}>
          {SHORTCUTS.map(s => (
            <div key={s.keys} style={{
              display: "flex", justifyContent: "space-between", alignItems: "center",
            }}>
              <span style={{ fontSize: 13, color: "var(--text-secondary)" }}>{s.description}</span>
              <kbd style={{
                background: "var(--bg-active)", borderRadius: "var(--radius-sm)",
                padding: "2px 8px", fontSize: 12, fontWeight: 600, fontFamily: "var(--font-mono)",
                color: "var(--text-primary)", border: "1px solid var(--border-default)",
              }}>{s.keys}</kbd>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
