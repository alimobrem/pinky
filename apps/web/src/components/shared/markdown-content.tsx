"use client";

import ReactMarkdown from "react-markdown";
import { cn } from "@/lib/utils";

interface MarkdownContentProps {
  content: string;
  className?: string;
}

export function MarkdownContent({ content, className }: MarkdownContentProps) {
  return (
    <div
      className={cn(
        "prose prose-sm prose-invert max-w-none",
        "prose-headings:text-text-primary prose-headings:font-semibold prose-headings:tracking-tight",
        "prose-h2:text-base prose-h2:mt-4 prose-h2:mb-2",
        "prose-h3:text-sm prose-h3:mt-3 prose-h3:mb-1.5",
        "prose-p:text-text-secondary prose-p:text-body-sm prose-p:leading-relaxed prose-p:my-1.5",
        "prose-strong:text-text-primary prose-strong:font-medium",
        "prose-code:rounded prose-code:bg-bg-hover prose-code:px-1.5 prose-code:py-0.5 prose-code:text-brand-purple prose-code:font-mono prose-code:text-xs prose-code:before:content-none prose-code:after:content-none",
        "prose-pre:bg-bg-hover prose-pre:rounded-lg prose-pre:border prose-pre:border-border-default",
        "prose-ul:text-text-secondary prose-ul:text-body-sm prose-ul:my-1.5 prose-ul:pl-4",
        "prose-ol:text-text-secondary prose-ol:text-body-sm prose-ol:my-1.5 prose-ol:pl-4",
        "prose-li:my-0.5",
        "prose-hr:border-border-subtle prose-hr:my-3",
        "prose-a:text-brand-pink prose-a:no-underline hover:prose-a:underline",
        className,
      )}
    >
      <ReactMarkdown>{content}</ReactMarkdown>
    </div>
  );
}
