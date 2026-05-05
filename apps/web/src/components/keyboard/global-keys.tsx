"use client";

import { useRouter } from "next/navigation";
import { useRef, useEffect, useCallback } from "react";

export function GlobalKeys() {
  const router = useRouter();
  const pendingRef = useRef<string | null>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      const target = e.target as HTMLElement;
      if (
        target.tagName === "INPUT" ||
        target.tagName === "TEXTAREA" ||
        target.tagName === "SELECT" ||
        target.isContentEditable
      ) {
        return;
      }

      if (e.metaKey || e.ctrlKey || e.altKey) return;

      const key = e.key.toLowerCase();

      if (pendingRef.current === "g") {
        pendingRef.current = null;
        if (timerRef.current) clearTimeout(timerRef.current);

        const routes: Record<string, string> = {
          d: "/dashboard",
          t: "/tasks",
          w: "/watch",
          h: "/history",
          a: "/alerts",
          s: "/settings",
        };

        if (routes[key]) {
          e.preventDefault();
          router.push(routes[key]);
        }
        return;
      }

      if (key === "g") {
        pendingRef.current = "g";
        if (timerRef.current) clearTimeout(timerRef.current);
        timerRef.current = setTimeout(() => {
          pendingRef.current = null;
        }, 500);
        return;
      }

      if (key === "?") {
        e.preventDefault();
        document.dispatchEvent(new CustomEvent("pinky:keyboard-help"));
      }
    },
    [router],
  );

  useEffect(() => {
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [handleKeyDown]);

  return null;
}
