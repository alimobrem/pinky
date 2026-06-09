import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import type { ReactNode } from "react";
import { EventBusProvider, useEventBus } from "./use-event-bus";

vi.mock("sonner", () => ({
  toast: {
    error: vi.fn(),
    warning: vi.fn(),
  },
}));

let mockOnAuthExpired: ((reason: string, clusterId?: string) => void) | undefined;

vi.mock("./use-sse", () => ({
  useSSE: (_url: string, opts: { onAuthExpired?: typeof mockOnAuthExpired }) => {
    mockOnAuthExpired = opts?.onAuthExpired;
    return {
      state: "connected" as const,
      lastUpdated: new Date(),
      retry: vi.fn(),
    };
  },
}));

function wrapper({ children }: { children: ReactNode }) {
  return <EventBusProvider>{children}</EventBusProvider>;
}

describe("useEventBus", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    mockOnAuthExpired = undefined;
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  it("returns connected state from provider", () => {
    const { result } = renderHook(() => useEventBus("test", vi.fn()), {
      wrapper,
    });
    expect(result.current.state).toBe("connected");
  });

  it("returns disconnected when outside provider", () => {
    const { result } = renderHook(() => useEventBus("test", vi.fn()));
    expect(result.current.state).toBe("disconnected");
  });

  it("returns lastUpdated from provider", () => {
    const { result } = renderHook(() => useEventBus("test", vi.fn()), {
      wrapper,
    });
    expect(result.current.lastUpdated).not.toBeNull();
  });
});

describe("EventBusProvider onAuthExpired", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    mockOnAuthExpired = undefined;
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  it("registers onAuthExpired callback", () => {
    renderHook(() => useEventBus("test", vi.fn()), { wrapper });
    expect(mockOnAuthExpired).toBeDefined();
  });

  it("shows toast and redirects on session expiry", async () => {
    const { toast } = await import("sonner");
    renderHook(() => useEventBus("test", vi.fn()), { wrapper });

    const locationSpy = vi.spyOn(window, "location", "get").mockReturnValue({
      ...window.location,
      href: "",
    });

    act(() => {
      mockOnAuthExpired?.("session_expired");
    });

    expect(toast.error).toHaveBeenCalledWith(
      "Session expired. Redirecting to login...",
    );

    locationSpy.mockRestore();
  });

  it("shows warning toast on binding expiry without redirect", async () => {
    const { toast } = await import("sonner");
    renderHook(() => useEventBus("test", vi.fn()), { wrapper });

    act(() => {
      mockOnAuthExpired?.("binding_expired", "cluster-abc");
    });

    expect(toast.warning).toHaveBeenCalledWith(
      expect.stringContaining("cluster-abc"),
    );
  });
});
