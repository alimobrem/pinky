"use client";

import {
  createContext,
  useContext,
  useEffect,
  useCallback,
  useId,
  useRef,
  type ReactNode,
} from "react";
import type { SSEEvent } from "@pinky/contracts";
import { useSSE, type SSEConnectionState } from "@/hooks/use-sse";
export type { SSEConnectionState } from "@/hooks/use-sse";

export type SSEEnvelope = Partial<SSEEvent> & { stream: string; aggregate_id: string; type: string };

type EventHandler = (data: SSEEnvelope) => void;

interface EventBusContext {
  subscribe: (id: string, handler: EventHandler) => () => void;
  state: SSEConnectionState;
  lastUpdated: Date | null;
}

const EventBusCtx = createContext<EventBusContext | null>(null);

export function EventBusProvider({ children }: { children: ReactNode }) {
  const subscribers = useRef(new Map<string, EventHandler>());

  const { state, lastUpdated } = useSSE("/api/v1/streams/events", {
    onEvent: {
      update: (data) => {
        try {
          const envelope: SSEEnvelope = typeof data === "string" ? JSON.parse(data) : data;
          for (const handler of subscribers.current.values()) {
            handler(envelope);
          }
        } catch (err) {
          console.warn("[EventBus] malformed SSE event:", err);
        }
      },
    },
  });

  const subscribe = useCallback((id: string, handler: EventHandler) => {
    subscribers.current.set(id, handler);
    return () => {
      subscribers.current.delete(id);
    };
  }, []);

  return (
    <EventBusCtx.Provider value={{ subscribe, state, lastUpdated }}>
      {children}
    </EventBusCtx.Provider>
  );
}

export function useEventBus(id: string, handler: EventHandler) {
  const ctx = useContext(EventBusCtx);
  const instanceId = useId();
  const subscriberKey = `${id}-${instanceId}`;
  const handlerRef = useRef(handler);
  handlerRef.current = handler;

  useEffect(() => {
    if (!ctx) return;
    return ctx.subscribe(subscriberKey, (data) => handlerRef.current(data));
  }, [ctx, subscriberKey]);

  return {
    state: ctx?.state ?? ("disconnected" as SSEConnectionState),
    lastUpdated: ctx?.lastUpdated ?? null,
  };
}
