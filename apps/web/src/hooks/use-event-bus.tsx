"use client";

import {
  createContext,
  useContext,
  useEffect,
  useCallback,
  useRef,
  type ReactNode,
} from "react";
import { useSSE, type SSEConnectionState } from "@/hooks/use-sse";

type EventHandler = (data: unknown) => void;

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
        for (const handler of subscribers.current.values()) {
          handler(data);
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
  const handlerRef = useRef(handler);
  handlerRef.current = handler;

  useEffect(() => {
    if (!ctx) return;
    return ctx.subscribe(id, (data) => handlerRef.current(data));
  }, [ctx, id]);

  return {
    state: ctx?.state ?? ("disconnected" as SSEConnectionState),
    lastUpdated: ctx?.lastUpdated ?? null,
  };
}
