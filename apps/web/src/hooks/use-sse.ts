"use client";

import { useEffect, useRef, useState, useCallback } from "react";

export type SSEConnectionState = "connecting" | "connected" | "reconnecting" | "disconnected";

export interface UseSSEOptions {
  /** Event handlers keyed by event type (e.g. "update", "heartbeat") */
  onEvent?: Record<string, (data: string) => void>;
  /** Called when connection state changes */
  onStateChange?: (state: SSEConnectionState) => void;
  /** Called on auth-expired or binding-expired sentinel events */
  onAuthExpired?: (reason: string, clusterId?: string) => void;
  /** Whether the hook is active (default true) */
  enabled?: boolean;
  /** Max reconnection attempts before giving up (default 20) */
  maxRetries?: number;
}

export interface UseSSEReturn {
  state: SSEConnectionState;
  lastUpdated: Date | null;
  retry: () => void;
}

const HEARTBEAT_TIMEOUT_MS = 45_000;
const BASE_DELAY_MS = 1_000;
const MAX_DELAY_MS = 30_000;

function backoffDelay(attempt: number): number {
  return Math.min(BASE_DELAY_MS * 2 ** attempt, MAX_DELAY_MS);
}

export function useSSE(url: string, options: UseSSEOptions = {}): UseSSEReturn {
  const { onEvent, onStateChange, onAuthExpired, enabled = true, maxRetries = 20 } = options;

  const [state, setState] = useState<SSEConnectionState>("connecting");
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const retriesRef = useRef(0);
  const esRef = useRef<EventSource | null>(null);
  const heartbeatTimerRef = useRef<ReturnType<typeof setTimeout>>(undefined);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout>>(undefined);
  const onEventRef = useRef(onEvent);
  const onAuthExpiredRef = useRef(onAuthExpired);
  const onStateChangeRef = useRef(onStateChange);

  onEventRef.current = onEvent;
  onAuthExpiredRef.current = onAuthExpired;
  onStateChangeRef.current = onStateChange;

  const updateState = useCallback((s: SSEConnectionState) => {
    setState(s);
    onStateChangeRef.current?.(s);
  }, []);

  const resetHeartbeat = useCallback(() => {
    clearTimeout(heartbeatTimerRef.current);
    heartbeatTimerRef.current = setTimeout(() => {
      esRef.current?.close();
      updateState("reconnecting");
    }, HEARTBEAT_TIMEOUT_MS);
  }, [updateState]);

  const connect = useCallback(() => {
    esRef.current?.close();
    clearTimeout(reconnectTimerRef.current);
    clearTimeout(heartbeatTimerRef.current);

    const es = new EventSource(url);
    esRef.current = es;
    updateState("connecting");

    es.onopen = () => {
      retriesRef.current = 0;
      updateState("connected");
      setLastUpdated(new Date());
      resetHeartbeat();
    };

    es.addEventListener("heartbeat", () => {
      setLastUpdated(new Date());
      resetHeartbeat();
      onEventRef.current?.heartbeat?.("");
    });

    es.addEventListener("auth-expired", (e) => {
      try {
        const data = JSON.parse(e.data);
        onAuthExpiredRef.current?.(data.reason, data.cluster_id);
      } catch {
        onAuthExpiredRef.current?.("session_expired");
      }
      es.close();
      updateState("disconnected");
    });

    es.addEventListener("binding-expired", (e) => {
      try {
        const data = JSON.parse(e.data);
        onAuthExpiredRef.current?.("binding_expired", data.cluster_id);
      } catch {
        onAuthExpiredRef.current?.("binding_expired");
      }
    });

    const knownEvents = ["heartbeat", "auth-expired", "binding-expired"];
    if (onEventRef.current) {
      for (const eventType of Object.keys(onEventRef.current)) {
        if (knownEvents.includes(eventType)) continue;
        es.addEventListener(eventType, (e) => {
          setLastUpdated(new Date());
          resetHeartbeat();
          onEventRef.current?.[eventType]?.(e.data);
        });
      }
    }

    es.onerror = () => {
      es.close();
      clearTimeout(heartbeatTimerRef.current);

      if (retriesRef.current >= maxRetries) {
        updateState("disconnected");
        return;
      }

      updateState("reconnecting");
      const delay = backoffDelay(retriesRef.current);
      retriesRef.current++;
      reconnectTimerRef.current = setTimeout(connect, delay);
    };
  }, [url, maxRetries, resetHeartbeat, updateState]);

  const retry = useCallback(() => {
    retriesRef.current = 0;
    connect();
  }, [connect]);

  useEffect(() => {
    if (!enabled) {
      esRef.current?.close();
      clearTimeout(heartbeatTimerRef.current);
      clearTimeout(reconnectTimerRef.current);
      updateState("disconnected");
      return;
    }

    connect();

    return () => {
      esRef.current?.close();
      clearTimeout(heartbeatTimerRef.current);
      clearTimeout(reconnectTimerRef.current);
    };
  }, [url, enabled, connect, updateState]);

  return { state, lastUpdated, retry };
}
