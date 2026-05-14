"use client";

import { useEffect, useRef, useState } from "react";
import { Copy, Check } from "lucide-react";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";

interface ExecutionEvent {
  id: string;
  execution_id: string;
  event_type: string;
  sequence: number;
  payload: Record<string, unknown>;
  occurred_at: string;
}

interface ExecutionTerminalProps {
  events: ExecutionEvent[];
  className?: string;
}

const GREEN = "\x1b[32m";
const RED = "\x1b[31m";
const GRAY = "\x1b[90m";
const YELLOW = "\x1b[33m";
const CYAN = "\x1b[36m";
const BOLD = "\x1b[1m";
const RESET = "\x1b[0m";

function formatEvent(event: ExecutionEvent): string[] {
  const lines: string[] = [];

  switch (event.event_type) {
    case "started": {
      const p = event.payload;
      const steps = p.steps ?? 0;
      lines.push(`${CYAN}${BOLD}▶ Remediation started${RESET} ${GRAY}(${steps} step${Number(steps) !== 1 ? "s" : ""})${RESET}`);
      break;
    }
    case "progress": {
      const p = event.payload;
      lines.push(`${YELLOW}━━ Step ${p.step}/${p.total}: ${p.description ?? ""}${RESET}`);
      break;
    }
    case "command": {
      const p = event.payload;
      const cmd = String(p.command ?? "");
      const output = String(p.output ?? "");
      const exitCode = Number(p.exit_code ?? 0);
      lines.push(`${GREEN}$${RESET} ${cmd}`);
      if (exitCode === 0) {
        lines.push(`${GRAY}${output}${RESET}`);
      } else {
        lines.push(`${RED}✗ ${output}${RESET}`);
      }
      break;
    }
    case "completed": {
      const passed = event.payload.verification_passed;
      if (passed) {
        lines.push(`${GREEN}${BOLD}✓ Remediation completed — verification passed${RESET}`);
      } else {
        lines.push(`${YELLOW}${BOLD}⚠ Remediation completed — verification failed${RESET}`);
      }
      break;
    }
    case "failed": {
      const reason = String(event.payload.reason ?? "unknown");
      lines.push(`${RED}${BOLD}✗ Remediation failed: ${reason}${RESET}`);
      break;
    }
    case "verified": {
      const p = event.payload;
      const passed = p.passed;
      if (passed) {
        lines.push(`${GREEN}✓ Verification passed${RESET}`);
      } else {
        lines.push(`${RED}✗ Verification failed${RESET}`);
      }
      const details = p.details as Record<string, unknown> | undefined;
      if (details) {
        for (const [k, v] of Object.entries(details)) {
          lines.push(`${GRAY}  ${k}: ${String(v)}${RESET}`);
        }
      }
      break;
    }
    default:
      break;
  }

  return lines;
}

export function ExecutionTerminal({ events, className }: ExecutionTerminalProps) {
  const termRef = useRef<HTMLDivElement>(null);
  const xtermRef = useRef<import("@xterm/xterm").Terminal | null>(null);
  const renderedCount = useRef(0);
  const [commands, setCommands] = useState<string[]>([]);
  const [copiedIdx, setCopiedIdx] = useState<number | null>(null);

  useEffect(() => {
    let term: import("@xterm/xterm").Terminal | null = null;
    let disposed = false;

    (async () => {
      const { Terminal } = await import("@xterm/xterm");
      const { FitAddon } = await import("@xterm/addon-fit");

      if (disposed || !termRef.current) return;

      term = new Terminal({
        disableStdin: true,
        cursorBlink: false,
        fontSize: 12,
        fontFamily: "Geist Mono, monospace",
        lineHeight: 1.4,
        scrollback: 200,
        rows: 20,
        theme: {
          background: "#09090f",
          foreground: "#e8e6f0",
          cursor: "#09090f",
          selectionBackground: "#a78bfa33",
          black: "#09090f",
          green: "#45c99a",
          red: "#ef6b6b",
          yellow: "#e8be3c",
          blue: "#6ba3f7",
          cyan: "#8b8ef0",
          white: "#e8e6f0",
          brightBlack: "#8585a0",
        },
      });

      const fit = new FitAddon();
      term.loadAddon(fit);
      term.open(termRef.current);
      fit.fit();
      xtermRef.current = term;

      const observer = new ResizeObserver(() => fit.fit());
      observer.observe(termRef.current);

      return () => observer.disconnect();
    })();

    return () => {
      disposed = true;
      term?.dispose();
      xtermRef.current = null;
      renderedCount.current = 0;
    };
  }, []);

  useEffect(() => {
    const term = xtermRef.current;
    if (!term) return;

    if (events.length < renderedCount.current) {
      term.reset();
      renderedCount.current = 0;
      setCommands([]);
    }
    const newEvents = events.slice(renderedCount.current);
    const newCommands: string[] = [];

    for (const event of newEvents) {
      const lines = formatEvent(event);
      for (const line of lines) {
        term.writeln(line);
      }
      if (event.event_type === "command" && event.payload.command) {
        newCommands.push(String(event.payload.command));
      }
    }

    renderedCount.current = events.length;
    if (newCommands.length > 0) {
      setCommands((prev) => [...prev, ...newCommands]);
    }
  }, [events]);

  const copyCommand = (cmd: string, idx: number) => {
    navigator.clipboard.writeText(cmd);
    setCopiedIdx(idx);
    toast.success("Copied");
    setTimeout(() => setCopiedIdx(null), 2000);
  };

  return (
    <div className={className}>
      <div
        ref={termRef}
        role="log"
        aria-label="Execution command output"
        aria-live="polite"
        className="rounded-lg border border-border-default overflow-hidden"
      />
      {commands.length > 0 && (
        <div className="mt-2 space-y-1">
          {commands.map((cmd, i) => (
            <div
              key={i}
              className="group flex items-center gap-2 rounded bg-bg-surface px-2 py-1"
            >
              <span className="text-text-tertiary">$</span>
              <code className="flex-1 font-mono text-xs text-brand-purple truncate">
                {cmd}
              </code>
              <Button
                variant="ghost"
                size="icon"
                className="h-5 w-5 opacity-0 group-hover:opacity-100"
                onClick={() => copyCommand(cmd, i)}
              >
                {copiedIdx === i ? <Check size={10} /> : <Copy size={10} />}
              </Button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
