import { cn } from "@/lib/utils";

interface KbdProps {
  keys: string;
  className?: string;
}

export function Kbd({ keys, className }: KbdProps) {
  const parts = keys.split("+");

  return (
    <span className={cn("inline-flex items-center gap-0.5", className)}>
      {parts.map((key, i) => (
        <kbd
          key={i}
          className="inline-flex h-5 min-w-[20px] items-center justify-center rounded border border-border-default bg-bg-elevated px-1 font-mono text-caption font-medium text-text-secondary"
        >
          {formatKey(key)}
        </kbd>
      ))}
    </span>
  );
}

function formatKey(key: string): string {
  const map: Record<string, string> = {
    meta: "⌘",
    cmd: "⌘",
    ctrl: "⌃",
    control: "⌃",
    shift: "⇧",
    alt: "⌥",
    enter: "↵",
    backspace: "⌫",
    escape: "esc",
    esc: "esc",
  };
  return map[key.toLowerCase()] ?? key.toUpperCase();
}
