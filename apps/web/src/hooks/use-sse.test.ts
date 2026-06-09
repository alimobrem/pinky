import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useSSE } from "./use-sse";

class MockEventSource {
  static instances: MockEventSource[] = [];
  url: string;
  onopen: (() => void) | null = null;
  onerror: (() => void) | null = null;
  readyState = 0;
  private listeners = new Map<string, ((e: MessageEvent) => void)[]>();

  constructor(url: string) {
    this.url = url;
    MockEventSource.instances.push(this);
  }

  addEventListener(type: string, handler: (e: MessageEvent) => void) {
    const handlers = this.listeners.get(type) ?? [];
    handlers.push(handler);
    this.listeners.set(type, handlers);
  }

  removeEventListener(type: string, handler: (e: MessageEvent) => void) {
    const handlers = this.listeners.get(type) ?? [];
    this.listeners.set(
      type,
      handlers.filter((h) => h !== handler),
    );
  }

  close = vi.fn();

  simulateOpen() {
    this.readyState = 1;
    this.onopen?.();
  }

  simulateEvent(type: string, data: string) {
    const event = new MessageEvent(type, { data });
    for (const handler of this.listeners.get(type) ?? []) {
      handler(event);
    }
  }

  simulateError() {
    this.onerror?.();
  }
}

describe("useSSE", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    MockEventSource.instances = [];
    vi.stubGlobal("EventSource", MockEventSource);
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  it("starts in connecting state and transitions to connected on open", () => {
    const { result } = renderHook(() => useSSE("/test"));
    expect(result.current.state).toBe("connecting");

    act(() => {
      MockEventSource.instances[0].simulateOpen();
    });

    expect(result.current.state).toBe("connected");
  });

  it("sets lastUpdated on open and update events", () => {
    const onEvent = { update: vi.fn() };
    const { result } = renderHook(() => useSSE("/test", { onEvent }));

    expect(result.current.lastUpdated).toBeNull();

    act(() => {
      MockEventSource.instances[0].simulateOpen();
    });

    expect(result.current.lastUpdated).not.toBeNull();
  });

  it("dispatches update events to handler", () => {
    const updateHandler = vi.fn();
    renderHook(() =>
      useSSE("/test", { onEvent: { update: updateHandler } }),
    );

    act(() => {
      MockEventSource.instances[0].simulateOpen();
    });

    act(() => {
      MockEventSource.instances[0].simulateEvent(
        "update",
        '{"type":"task.updated"}',
      );
    });

    expect(updateHandler).toHaveBeenCalledWith('{"type":"task.updated"}');
  });

  it("reconnects with exponential backoff on error", () => {
    renderHook(() => useSSE("/test", { maxRetries: 5 }));

    act(() => {
      MockEventSource.instances[0].simulateError();
    });

    expect(MockEventSource.instances[0].close).toHaveBeenCalled();

    act(() => {
      vi.advanceTimersByTime(1000);
    });

    expect(MockEventSource.instances).toHaveLength(2);

    act(() => {
      MockEventSource.instances[1].simulateError();
    });

    act(() => {
      vi.advanceTimersByTime(2000);
    });

    expect(MockEventSource.instances).toHaveLength(3);
  });

  it("transitions to disconnected after max retries", () => {
    const { result } = renderHook(() => useSSE("/test", { maxRetries: 2 }));

    act(() => {
      MockEventSource.instances[0].simulateError();
    });
    act(() => {
      vi.advanceTimersByTime(1000);
    });
    act(() => {
      MockEventSource.instances[1].simulateError();
    });
    act(() => {
      vi.advanceTimersByTime(2000);
    });
    act(() => {
      MockEventSource.instances[2].simulateError();
    });

    expect(result.current.state).toBe("disconnected");
  });

  it("resets retry counter on successful reconnect", () => {
    const { result } = renderHook(() => useSSE("/test", { maxRetries: 3 }));

    act(() => {
      MockEventSource.instances[0].simulateError();
    });
    act(() => {
      vi.advanceTimersByTime(1000);
    });
    act(() => {
      MockEventSource.instances[1].simulateOpen();
    });

    expect(result.current.state).toBe("connected");

    act(() => {
      MockEventSource.instances[1].simulateError();
    });
    act(() => {
      vi.advanceTimersByTime(1000);
    });
    act(() => {
      MockEventSource.instances[2].simulateError();
    });
    act(() => {
      vi.advanceTimersByTime(2000);
    });
    act(() => {
      MockEventSource.instances[3].simulateOpen();
    });

    expect(result.current.state).toBe("connected");
  });

  it("calls onAuthExpired on auth-expired event and closes", () => {
    const onAuthExpired = vi.fn();
    const { result } = renderHook(() =>
      useSSE("/test", { onAuthExpired }),
    );

    act(() => {
      MockEventSource.instances[0].simulateOpen();
    });

    act(() => {
      MockEventSource.instances[0].simulateEvent(
        "auth-expired",
        '{"reason":"session_timeout"}',
      );
    });

    expect(onAuthExpired).toHaveBeenCalledWith("session_timeout", undefined);
    expect(result.current.state).toBe("disconnected");
    expect(MockEventSource.instances[0].close).toHaveBeenCalled();
  });

  it("calls onAuthExpired with cluster_id on binding-expired event", () => {
    const onAuthExpired = vi.fn();
    renderHook(() => useSSE("/test", { onAuthExpired }));

    act(() => {
      MockEventSource.instances[0].simulateOpen();
    });

    act(() => {
      MockEventSource.instances[0].simulateEvent(
        "binding-expired",
        '{"cluster_id":"cluster-123"}',
      );
    });

    expect(onAuthExpired).toHaveBeenCalledWith(
      "binding_expired",
      "cluster-123",
    );
  });

  it("handles malformed auth-expired data gracefully", () => {
    const onAuthExpired = vi.fn();
    renderHook(() => useSSE("/test", { onAuthExpired }));

    act(() => {
      MockEventSource.instances[0].simulateOpen();
    });

    act(() => {
      MockEventSource.instances[0].simulateEvent(
        "auth-expired",
        "not-json",
      );
    });

    expect(onAuthExpired).toHaveBeenCalledWith("session_expired");
  });

  it("reconnects on heartbeat timeout", () => {
    const { result } = renderHook(() => useSSE("/test"));

    act(() => {
      MockEventSource.instances[0].simulateOpen();
    });

    expect(result.current.state).toBe("connected");

    act(() => {
      vi.advanceTimersByTime(45_000);
    });

    expect(result.current.state).toBe("reconnecting");
    expect(MockEventSource.instances[0].close).toHaveBeenCalled();
  });

  it("resets heartbeat timer on update events", () => {
    const { result } = renderHook(() => useSSE("/test"));

    act(() => {
      MockEventSource.instances[0].simulateOpen();
    });

    act(() => {
      vi.advanceTimersByTime(40_000);
    });

    act(() => {
      MockEventSource.instances[0].simulateEvent("update", "{}");
    });

    act(() => {
      vi.advanceTimersByTime(40_000);
    });

    expect(result.current.state).toBe("connected");

    act(() => {
      vi.advanceTimersByTime(5_000);
    });

    expect(result.current.state).toBe("reconnecting");
  });

  it("does not connect when enabled=false", () => {
    const { result } = renderHook(() =>
      useSSE("/test", { enabled: false }),
    );

    expect(result.current.state).toBe("disconnected");
    expect(MockEventSource.instances).toHaveLength(0);
  });

  it("retry resets retries and reconnects", () => {
    const { result } = renderHook(() => useSSE("/test", { maxRetries: 1 }));

    act(() => {
      MockEventSource.instances[0].simulateError();
    });
    act(() => {
      vi.advanceTimersByTime(1000);
    });
    act(() => {
      MockEventSource.instances[1].simulateError();
    });

    expect(result.current.state).toBe("disconnected");

    act(() => {
      result.current.retry();
    });

    const latest = MockEventSource.instances[MockEventSource.instances.length - 1];
    act(() => {
      latest.simulateOpen();
    });

    expect(result.current.state).toBe("connected");
  });
});
