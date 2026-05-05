"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { NAV_ITEMS } from "@/components/nav-config";
import { cn } from "@/lib/utils";

export function MobileNav() {
  const pathname = usePathname();
  const items = NAV_ITEMS;

  return (
    <nav className="fixed inset-x-0 bottom-0 z-40 border-t border-border-subtle bg-bg-primary/90 px-2 pb-[env(safe-area-inset-bottom,0px)] pt-1.5 backdrop-blur-lg md:hidden">
      <div className="mx-auto flex max-w-full gap-1 overflow-x-auto">
        {items.map((item) => {
          const Icon = item.icon;
          const active = pathname.startsWith(item.path);
          return (
            <Link
              key={item.id}
              href={item.path}
              className={cn(
                "flex min-w-0 flex-1 flex-col items-center gap-1 rounded-xl px-2 py-2 text-xs font-medium no-underline transition-colors",
                active
                  ? "bg-bg-elevated text-text-primary"
                  : "text-text-tertiary hover:bg-bg-surface hover:text-text-secondary",
              )}
            >
              <Icon size={18} className={cn("transition-colors", active ? "text-accent-brand" : "")} />
              <span className="truncate">{item.label}</span>
            </Link>
          );
        })}
      </div>
    </nav>
  );
}
