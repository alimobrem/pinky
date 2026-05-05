"use client";

import type { ReactNode } from "react";
import { EnvStripe } from "@/components/shell/env-stripe";
import { IconRail } from "@/components/shell/icon-rail";
import { DetailPanel } from "@/components/shell/detail-panel";
import { TopBar } from "@/components/shell/top-bar";
import { MobileNav } from "@/components/shell/mobile-nav";
import { useDetailPanel } from "@/hooks/use-detail-panel";
import { ScrollArea } from "@/components/ui/scroll-area";
import { CommandProvider } from "@/components/command-palette/command-context";
import { CommandPalette } from "@/components/command-palette/command-palette";
import { GlobalKeys } from "@/components/keyboard/global-keys";
import { KeyboardHelp } from "@/components/keyboard/keyboard-help";

interface AppShellProps {
  children: ReactNode;
}

export function AppShell({ children }: AppShellProps) {
  const { isOpen, toggle, close } = useDetailPanel();

  return (
    <CommandProvider>
      <div className="flex h-screen flex-col overflow-hidden bg-bg-base">
        <EnvStripe />
        <div className="flex min-h-0 flex-1">
          <IconRail />
          <DetailPanel isOpen={isOpen} onClose={close} />
          <div className="flex min-w-0 flex-1 flex-col">
            <TopBar onTogglePanel={toggle} panelOpen={isOpen} />
            <ScrollArea className="flex-1">
              <main className="min-w-0 px-4 py-5 pb-20 sm:px-6 sm:py-6 md:pb-6 lg:px-8">
                <div className="mx-auto w-full max-w-[1400px]">
                  {children}
                </div>
              </main>
            </ScrollArea>
          </div>
        </div>
        <MobileNav />
        <CommandPalette />
        <KeyboardHelp />
        <GlobalKeys />
      </div>
    </CommandProvider>
  );
}
