import type { ReactNode } from "react";
import { NavRail } from "@/components/nav-rail";
import { TopBar } from "@/components/top-bar";

export default function ProductLayout({ children }: { children: ReactNode }) {
  return (
    <div style={{ display: "flex", minHeight: "100vh" }}>
      <NavRail />
      <div style={{ flex: 1, display: "flex", flexDirection: "column" }}>
        <TopBar />
        <main style={{ flex: 1, padding: "var(--space-6)" }}>
          {children}
        </main>
      </div>
    </div>
  );
}
