"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { NAV_ITEMS } from "@/components/shell/nav-config";

export function MobileNav() {
  const pathname = usePathname();
  const items = NAV_ITEMS.filter((i) => i.section === "primary").slice(0, 5);

  return (
    <nav className="fixed inset-x-0 bottom-0 z-50 flex h-14 items-center justify-around border-t border-border-subtle bg-bg-inset/95 backdrop-blur-sm md:hidden">
      {items.map((item) => {
        const active = pathname.startsWith(item.path);
        const Icon = item.icon;

        return (
          <Link
            key={item.id}
            href={item.path}
            aria-label={item.label}
            aria-current={active ? "page" : undefined}
            className={cn(
              "flex flex-col items-center gap-0.5 px-3 py-1 no-underline transition-colors",
              active ? "text-brand-pink" : "text-text-tertiary",
            )}
          >
            <Icon size={20} strokeWidth={active ? 2 : 1.5} />
            <span className="text-caption font-medium">{item.label}</span>
          </Link>
        );
      })}
    </nav>
  );
}
