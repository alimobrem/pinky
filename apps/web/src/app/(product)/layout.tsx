import type { ReactNode } from "react";
import { NavRail } from "@/components/nav-rail";
import { TopBar } from "@/components/top-bar";
import { CommandPalette } from "@/components/command-palette";
import { ToastProvider } from "@/components/toast";

export default function ProductLayout({ children }: { children: ReactNode }) {
  return (
    <ToastProvider>
      <div style={{ display: "flex", minHeight: "100vh" }}>
        <NavRail />
        <div style={{ flex: 1, display: "flex", flexDirection: "column" }}>
          <TopBar />
          <main style={{ flex: 1, padding: "var(--space-6)", overflowY: "auto" }}>
            {children}
          </main>
        </div>
      </div>
      <CommandPalette />
    </ToastProvider>
  );
}
