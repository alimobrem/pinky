"use client";

import { useEffect, useRef } from "react";

type KeyCombo = string;

export function useHotkey(
  key: KeyCombo,
  callback: (e: KeyboardEvent) => void,
  opts?: { enabled?: boolean },
) {
  const cbRef = useRef(callback);
  cbRef.current = callback;

  useEffect(() => {
    if (opts?.enabled === false) return;

    function handler(e: KeyboardEvent) {
      const target = e.target as HTMLElement;
      if (
        target.tagName === "INPUT" ||
        target.tagName === "TEXTAREA" ||
        target.tagName === "SELECT" ||
        target.isContentEditable
      ) {
        return;
      }

      const parts = key.toLowerCase().split("+");
      const mainKey = parts[parts.length - 1];
      const needsMeta = parts.includes("meta") || parts.includes("cmd");
      const needsCtrl = parts.includes("ctrl") || parts.includes("control");
      const needsShift = parts.includes("shift");
      const needsAlt = parts.includes("alt");

      if (needsMeta && !e.metaKey) return;
      if (needsCtrl && !e.ctrlKey) return;
      if (needsShift && !e.shiftKey) return;
      if (needsAlt && !e.altKey) return;

      if (e.key.toLowerCase() === mainKey) {
        e.preventDefault();
        cbRef.current(e);
      }
    }

    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [key, opts?.enabled]);
}
