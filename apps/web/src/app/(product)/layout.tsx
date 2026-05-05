export const dynamic = "force-dynamic";

import type { ReactNode } from "react";
import { NavRail } from "@/components/nav-rail";
import { TopBar } from "@/components/top-bar";
import { CommandPalette } from "@/components/command-palette";
import { KeyboardHelp } from "@/components/keyboard-help";
import { GlobalKeys } from "@/components/global-keys";
import { MobileNav } from "@/components/mobile-nav";
import { requireServerSession } from "@/lib/server-auth";

export default async function ProductLayout({ children }: { children: ReactNode }) {
  await requireServerSession();

  return (
    <div className="flex h-screen overflow-hidden bg-[radial-gradient(circle_at_top_left,rgba(167,139,250,0.08),transparent_28%),radial-gradient(circle_at_top_right,rgba(244,114,182,0.06),transparent_24%),#08070d]">
      <NavRail />
      <div className="flex min-w-0 flex-1 flex-col overflow-hidden">
        <TopBar />
        <main className="min-w-0 flex-1 overflow-x-hidden overflow-y-auto px-5 py-7 pb-24 sm:px-6 sm:py-8 sm:pb-24 md:pb-8 lg:px-8 lg:py-8 xl:px-10">
          <div className="mx-auto flex min-w-0 w-full max-w-[1440px] flex-col">
            {children}
          </div>
        </main>
      </div>
      <MobileNav />
      <CommandPalette />
      <KeyboardHelp />
      <GlobalKeys />
    </div>
  );
}
