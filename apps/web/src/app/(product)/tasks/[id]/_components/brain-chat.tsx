"use client";

import { useState, useRef, useEffect } from "react";
import { useMutation } from "@tanstack/react-query";
import { Brain, Send, Copy } from "lucide-react";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { MarkdownContent } from "@/components/shared/markdown-content";
import { MetricChart } from "@/components/shared/metric-chart";
import type { ChartData } from "@pinky/contracts";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { ChevronRight } from "lucide-react";
import { toast } from "sonner";

interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  commands?: string[];
  charts?: ChartData[];
}

interface BrainChatProps {
  taskId: string;
  className?: string;
}

export function BrainChat({ taskId, className }: BrainChatProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [isOpen, setIsOpen] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  const chat = useMutation({
    mutationFn: async (message: string) => {
      const res = await api.post<{ reply: string; commands?: string[]; charts?: ChartData[] }>(
        `/api/v1/work-items/${taskId}/chat`,
        { message, history: messages },
      );
      return res;
    },
    onSuccess: (data) => {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: data.reply, commands: data.commands, charts: data.charts },
      ]);
    },
    onError: () => {
      toast.error("Failed to get response from The Brain");
    },
  });

  const handleSend = () => {
    if (!input.trim() || chat.isPending) return;
    const msg = input.trim();
    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: msg }]);
    chat.mutate(msg);
  };

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages]);

  const copyCommand = (cmd: string) => {
    navigator.clipboard.writeText(cmd);
    toast.success("Copied");
  };

  return (
    <Collapsible open={isOpen} onOpenChange={setIsOpen} className={className}>
      <CollapsibleTrigger className="flex w-full items-center gap-2 rounded-lg border border-border-default bg-bg-surface px-4 py-3 text-sm font-medium text-text-primary transition-colors hover:bg-bg-hover">
        <Brain size={16} className="text-brand-purple" />
        <span className="flex-1 text-left">Ask The Brain</span>
        <ChevronRight
          size={14}
          className={cn(
            "text-text-tertiary transition-transform",
            isOpen && "rotate-90",
          )}
        />
      </CollapsibleTrigger>
      <CollapsibleContent className="mt-2">
        <div className="rounded-lg border border-border-default bg-bg-surface overflow-hidden">
          <div
            ref={scrollRef}
            className="max-h-80 overflow-y-auto p-4 space-y-4"
          >
            {messages.length === 0 && (
              <div className="text-center py-8">
                <Brain size={24} className="mx-auto text-text-tertiary mb-2" />
                <p className="text-body-sm text-text-secondary">
                  Ask about the investigation, request YAML, or get help with remediation
                </p>
                <div className="flex flex-wrap justify-center gap-2 mt-3">
                  {[
                    "Why did you recommend this?",
                    "Show me the YAML",
                    "What's the risk?",
                  ].map((q) => (
                    <button
                      key={q}
                      type="button"
                      className="rounded-full border border-border-default px-3 py-1 text-caption text-text-secondary hover:border-brand-purple hover:text-brand-purple transition-colors"
                      onClick={() => {
                        setInput(q);
                        setMessages((prev) => [...prev, { role: "user", content: q }]);
                        chat.mutate(q);
                      }}
                    >
                      {q}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {messages.map((msg, i) => (
              <div
                key={i}
                className={cn(
                  "flex gap-3",
                  msg.role === "user" ? "justify-end" : "justify-start",
                )}
              >
                {msg.role === "assistant" && (
                  <Brain size={16} className="mt-1 shrink-0 text-brand-purple" />
                )}
                <div
                  className={cn(
                    "max-w-[85%] rounded-lg px-3 py-2",
                    msg.role === "user"
                      ? "bg-brand-purple/10 text-text-primary"
                      : "bg-bg-hover",
                  )}
                >
                  {msg.role === "assistant" ? (
                    <MarkdownContent content={msg.content} />
                  ) : (
                    <p className="text-sm text-text-primary">{msg.content}</p>
                  )}
                  {msg.charts && msg.charts.length > 0 && (
                    <div className="mt-3 space-y-3">
                      {msg.charts.map((chart, k) => (
                        <MetricChart key={k} chart={chart} />
                      ))}
                    </div>
                  )}
                  {msg.commands && msg.commands.length > 0 && (
                    <div className="mt-2 space-y-1">
                      {msg.commands.map((cmd, j) => (
                        <div
                          key={j}
                          className="group flex items-center gap-2 rounded bg-bg-surface px-2 py-1"
                        >
                          <span className="text-text-tertiary">$</span>
                          <code className="flex-1 font-mono text-xs text-brand-purple">
                            {cmd}
                          </code>
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-5 w-5 opacity-0 group-hover:opacity-100"
                            onClick={() => copyCommand(cmd)}
                          >
                            <Copy size={10} />
                          </Button>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            ))}

            {chat.isPending && (
              <div className="flex items-center gap-2 text-text-tertiary">
                <Brain size={16} className="animate-pulse text-brand-purple" />
                <span className="text-caption">Thinking...</span>
              </div>
            )}
          </div>

          <div className="flex items-center gap-2 border-t border-border-default px-3 py-2">
            <Input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSend()}
              placeholder="Ask about this investigation..."
              className="h-8 border-0 bg-transparent text-sm shadow-none focus-visible:ring-0"
              disabled={chat.isPending}
            />
            <Button
              variant="ghost"
              size="icon"
              className="h-7 w-7 text-brand-purple"
              onClick={handleSend}
              disabled={!input.trim() || chat.isPending}
            >
              <Send size={14} />
            </Button>
          </div>
        </div>
      </CollapsibleContent>
    </Collapsible>
  );
}
