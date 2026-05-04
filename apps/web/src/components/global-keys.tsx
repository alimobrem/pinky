"use client";

import { useEffect, useRef } from "react";
import { useRouter } from "next/navigation";

const GO_ROUTES: Record<string, string> = {
  d: "/dashboard",
  t: "/tasks",
  w: "/watch",
  h: "/history",
  a: "/alerts",
  s: "/settings",
};

export function GlobalKeys() {
  const router = useRouter();
  const pendingG = useRef(false);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLSelectElement || e.target instanceof HTMLTextAreaElement) return;
      if (e.metaKey || e.ctrlKey || e.altKey) return;

      if (pendingG.current) {
        pendingG.current = false;
        const route = GO_ROUTES[e.key];
        if (route) { e.preventDefault(); router.push(route); }
        return;
      }

      if (e.key === "g") {
        pendingG.current = true;
        setTimeout(() => { pendingG.current = false; }, 500);
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [router]);

  return null;
}
