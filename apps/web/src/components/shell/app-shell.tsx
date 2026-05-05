"use client";

import type { ReactNode } from "react";
import { EnvStripe } from "@/components/shell/env-stripe";
import { Sidebar } from "@/components/shell/sidebar";
import { TopBar } from "@/components/shell/top-bar";
import { MobileNav } from "@/components/shell/mobile-nav";
import { CommandProvider } from "@/components/command-palette/command-context";
import { CommandPalette } from "@/components/command-palette/command-palette";
import { GlobalKeys } from "@/components/keyboard/global-keys";
import { KeyboardHelp } from "@/components/keyboard/keyboard-help";

interface AppShellProps {
  children: ReactNode;
}

export function AppShell({ children }: AppShellProps) {
  return (
    <CommandProvider>
      <div className="flex h-screen flex-col overflow-hidden bg-bg-base">
        <EnvStripe />
        <div className="flex min-h-0 flex-1 overflow-hidden">
          <Sidebar />
          <div className="flex min-w-0 flex-1 flex-col">
            <TopBar />
            <main className="flex-1 overflow-x-hidden overflow-y-auto">
              <div className="px-6 py-6 pb-20 sm:px-8 sm:py-8 md:pb-8 lg:px-10 lg:py-8 xl:px-12">
                <div className="mx-auto w-full max-w-[1400px]">
                  {children}
                </div>
              </div>
            </main>
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
