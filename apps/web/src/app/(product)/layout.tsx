export const dynamic = "force-dynamic";

import type { ReactNode } from "react";
import { NavRail } from "@/components/nav-rail";
import { TopBar } from "@/components/top-bar";
import { CommandPalette } from "@/components/command-palette";
import { KeyboardHelp } from "@/components/keyboard-help";

export default function ProductLayout({ children }: { children: ReactNode }) {
  return (
    <div className="flex min-h-screen">
      <NavRail />
      <div className="flex flex-1 flex-col">
        <TopBar />
        <main className="flex-1 overflow-y-auto p-6">
          {children}
        </main>
      </div>
      <CommandPalette />
      <KeyboardHelp />
    </div>
  );
}
