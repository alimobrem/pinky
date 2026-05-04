export const dynamic = "force-dynamic";

import type { ReactNode } from "react";
import { NavRail } from "@/components/nav-rail";
import { TopBar } from "@/components/top-bar";
import { CommandPalette } from "@/components/command-palette";
import { KeyboardHelp } from "@/components/keyboard-help";
import { GlobalKeys } from "@/components/global-keys";
import { requireServerSession } from "@/lib/server-auth";

export default async function ProductLayout({ children }: { children: ReactNode }) {
  await requireServerSession();

  return (
    <div className="flex min-h-screen">
      <NavRail />
      <div className="flex flex-1 flex-col">
        <TopBar />
        <main className="flex-1 overflow-y-auto px-4 py-5 sm:px-6 sm:py-6 lg:px-8 lg:py-8">
          <div className="mx-auto flex w-full max-w-[1440px] flex-col">
            {children}
          </div>
        </main>
      </div>
      <CommandPalette />
      <KeyboardHelp />
      <GlobalKeys />
    </div>
  );
}
