"use client";

import { useEffect, useState } from "react";
import { X } from "lucide-react";
import { Button } from "@/components/ui/button";

const SHORTCUT_GROUPS = [
  {
    title: "Navigation",
    shortcuts: [
      { keys: "g d", description: "Go to Dashboard" },
      { keys: "g t", description: "Go to Tasks" },
      { keys: "g w", description: "Go to Watch" },
      { keys: "g s", description: "Go to Settings" },
    ],
  },
  {
    title: "Tasks",
    shortcuts: [
      { keys: "j / k", description: "Navigate task list" },
      { keys: "Enter", description: "Open focused task" },
      { keys: "a", description: "Accept focused task" },
      { keys: "s", description: "Start focused task" },
      { keys: "c", description: "Complete focused task" },
      { keys: "b", description: "Block focused task" },
      { keys: "x", description: "Toggle select" },
      { keys: "/", description: "Focus search" },
    ],
  },
  {
    title: "Global",
    shortcuts: [
      { keys: "⌘K", description: "Command palette" },
      { keys: "?", description: "Keyboard shortcuts" },
      { keys: "Escape", description: "Close dialog" },
    ],
  },
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
      className="fixed inset-0 z-[150] bg-black/60 backdrop-blur-sm flex items-center justify-center"
      onClick={() => setOpen(false)}
    >
      <div onClick={e => e.stopPropagation()} className="w-[480px] bg-popover border border-border rounded-xl shadow-dropdown p-6">
        <div className="flex justify-between items-center mb-6">
          <h2 className="text-base font-semibold">Keyboard Shortcuts</h2>
          <Button variant="ghost" size="sm" onClick={() => setOpen(false)} aria-label="Close" className="text-text-tertiary hover:text-text-primary h-8 w-8 p-0">
            <X size={18} />
          </Button>
        </div>

        <div className="space-y-6">
          {SHORTCUT_GROUPS.map(group => (
            <div key={group.title}>
              <div className="text-xs font-semibold text-text-tertiary uppercase tracking-wider mb-3">{group.title}</div>
              <div className="flex flex-col gap-2.5">
                {group.shortcuts.map(s => (
                  <div key={s.keys} className="flex justify-between items-center">
                    <span className="text-sm text-text-secondary">{s.description}</span>
                    <kbd className="bg-bg-active rounded px-2 py-0.5 text-xs font-semibold font-mono text-text-primary border border-border-default min-w-[40px] text-center">{s.keys}</kbd>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
