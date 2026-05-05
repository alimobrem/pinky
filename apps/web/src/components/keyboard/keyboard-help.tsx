"use client";

import { useState, useEffect } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Kbd } from "@/components/shared/keyboard-shortcut-hint";

const SHORTCUTS = [
  { section: "Navigation", items: [
    { keys: "g+d", label: "Go to Dashboard" },
    { keys: "g+t", label: "Go to Tasks" },
    { keys: "g+w", label: "Go to Watch" },
    { keys: "g+h", label: "Go to History" },
    { keys: "g+a", label: "Go to Alerts" },
    { keys: "g+s", label: "Go to Settings" },
  ]},
  { section: "Search", items: [
    { keys: "cmd+k", label: "Command palette" },
    { keys: "/", label: "Focus search" },
  ]},
  { section: "Tasks", items: [
    { keys: "j", label: "Next item" },
    { keys: "k", label: "Previous item" },
    { keys: "enter", label: "Open item" },
    { keys: "x", label: "Select item" },
    { keys: "a", label: "Accept task" },
    { keys: "s", label: "Start task" },
    { keys: "c", label: "Complete task" },
  ]},
  { section: "General", items: [
    { keys: "?", label: "Keyboard shortcuts" },
    { keys: "escape", label: "Close / cancel" },
  ]},
];

export function KeyboardHelp() {
  const [open, setOpen] = useState(false);

  useEffect(() => {
    function handler() {
      setOpen(true);
    }
    document.addEventListener("pinky:keyboard-help", handler);
    return () => document.removeEventListener("pinky:keyboard-help", handler);
  }, []);

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>Keyboard shortcuts</DialogTitle>
        </DialogHeader>
        <div className="space-y-5 py-2">
          {SHORTCUTS.map((section) => (
            <div key={section.section}>
              <h3 className="mb-2 text-[11px] font-semibold uppercase tracking-widest text-text-tertiary">
                {section.section}
              </h3>
              <div className="space-y-1.5">
                {section.items.map((item) => (
                  <div
                    key={item.keys}
                    className="flex items-center justify-between py-0.5"
                  >
                    <span className="text-sm text-text-secondary">{item.label}</span>
                    <Kbd keys={item.keys} />
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </DialogContent>
    </Dialog>
  );
}
