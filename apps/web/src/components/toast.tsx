"use client";

import { createContext, useCallback, useContext, useState, type ReactNode } from "react";
import { CheckCircle, AlertTriangle, X, Info } from "lucide-react";

type ToastType = "success" | "error" | "warning" | "info";

interface Toast {
  id: string;
  message: string;
  type: ToastType;
}

interface ToastContextValue {
  toast: (message: string, type?: ToastType) => void;
}

const ToastContext = createContext<ToastContextValue>({ toast: () => {} });

export function useToast() {
  return useContext(ToastContext);
}

const ICONS: Record<ToastType, ReactNode> = {
  success: <CheckCircle size={16} />,
  error: <AlertTriangle size={16} />,
  warning: <AlertTriangle size={16} />,
  info: <Info size={16} />,
};

const COLORS: Record<ToastType, string> = {
  success: "var(--status-done)",
  error: "var(--status-blocked)",
  warning: "var(--status-in-progress)",
  info: "var(--status-ready)",
};

const DURATIONS: Record<ToastType, number> = {
  success: 4000,
  error: 8000,
  warning: 6000,
  info: 4000,
};

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const addToast = useCallback((message: string, type: ToastType = "info") => {
    const id = Math.random().toString(36).slice(2);
    setToasts(prev => [...prev.slice(-2), { id, message, type }]);
    setTimeout(() => {
      setToasts(prev => prev.filter(t => t.id !== id));
    }, DURATIONS[type]);
  }, []);

  const removeToast = useCallback((id: string) => {
    setToasts(prev => prev.filter(t => t.id !== id));
  }, []);

  return (
    <ToastContext.Provider value={{ toast: addToast }}>
      {children}
      {/* Toast container */}
      <div style={{
        position: "fixed", bottom: "var(--space-5)", right: "var(--space-5)",
        zIndex: 200, display: "flex", flexDirection: "column-reverse",
        gap: "var(--space-2)", maxWidth: 380,
      }}>
        {toasts.map(t => (
          <div key={t.id} style={{
            background: "var(--bg-elevated)", border: "1px solid var(--border-default)",
            borderLeft: `3px solid ${COLORS[t.type]}`,
            borderRadius: "var(--radius-lg)", padding: "var(--space-3) var(--space-4)",
            boxShadow: "var(--shadow-elevated)",
            display: "flex", alignItems: "center", gap: "var(--space-3)",
            animation: "slide-in 300ms ease-out",
            fontSize: 13,
          }}>
            <span style={{ color: COLORS[t.type], flexShrink: 0 }}>{ICONS[t.type]}</span>
            <span style={{ flex: 1 }}>{t.message}</span>
            <button onClick={() => removeToast(t.id)} style={{
              background: "none", border: "none", color: "var(--text-tertiary)",
              cursor: "pointer", padding: 2, flexShrink: 0,
            }}>
              <X size={14} />
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}
