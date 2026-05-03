"use client";

import { useEffect, useState } from "react";
import { X } from "lucide-react";

const SHORTCUTS = [
  { keys: "⌘K", description: "Open command palette" },
  { keys: "j / k", description: "Navigate list items" },
  { keys: "Enter", description: "Open selected item" },
  { keys: "a / s / b / c", description: "Accept / Start / Block / Complete task" },
  { keys: "Escape", description: "Close dialog / go back" },
  { keys: "?", description: "Show keyboard shortcuts" },
];

export function KeyboardHelp() {
  const [open, setOpen] = useState(false);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLSelectElement || e.target instanceof HTMLTextAreaElement) return;
      if (e.key === "?" && !e.metaKey && !e.ctrlKey) { e.preventDefault(); setOpen(o => !o); }
      if (e.key === "Escape") setOpen(false);
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, []);

  if (!open) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Keyboard shortcuts"
      className="fixed inset-0 z-150 bg-black/60 backdrop-blur-sm flex items-center justify-center"
      onClick={() => setOpen(false)}
    >
      <div onClick={e => e.stopPropagation()} className="w-[400px] bg-bg-elevated border border-border-default rounded-xl shadow-dropdown p-6">
        <div className="flex justify-between items-center mb-5">
          <h2 className="text-base font-semibold">Keyboard Shortcuts</h2>
          <button onClick={() => setOpen(false)} aria-label="Close" className="text-text-tertiary hover:text-text-primary bg-transparent border-none cursor-pointer">
            <X size={18} />
          </button>
        </div>

        <div className="flex flex-col gap-3">
          {SHORTCUTS.map(s => (
            <div key={s.keys} className="flex justify-between items-center">
              <span className="text-sm text-text-secondary">{s.description}</span>
              <kbd className="bg-bg-active rounded-sm px-2 py-0.5 text-xs font-semibold font-mono text-text-primary border border-border-default">{s.keys}</kbd>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
