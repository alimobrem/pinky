import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { useRetryableMutation } from "./use-retryable-mutation";

vi.mock("sonner", () => {
  const errorFn = vi.fn();
  return { toast: { error: errorFn } };
});

function createWrapper() {
  const qc = new QueryClient({
    defaultOptions: { mutations: { retry: false } },
  });
  function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
  }
  return Wrapper;
}

describe("useRetryableMutation", () => {
  let mockToast: ReturnType<typeof vi.fn>;

  beforeEach(async () => {
    vi.clearAllMocks();
    const { toast } = await import("sonner");
    mockToast = toast.error as ReturnType<typeof vi.fn>;
  });

  it("calls mutationFn on mutate", async () => {
    const fn = vi.fn().mockResolvedValue("ok");
    const { result } = renderHook(
      () =>
        useRetryableMutation({
          errorMessage: "Failed",
          mutationFn: fn,
        }),
      { wrapper: createWrapper() },
    );

    act(() => {
      result.current.mutate("arg1" as never);
    });

    await waitFor(() =>
      expect(fn).toHaveBeenCalledWith("arg1", expect.anything()),
    );
  });

  it("shows toast with retry action on error", async () => {
    const fn = vi.fn().mockRejectedValue(new Error("boom"));
    const { result } = renderHook(
      () =>
        useRetryableMutation({
          errorMessage: "Save failed",
          mutationFn: fn,
        }),
      { wrapper: createWrapper() },
    );

    act(() => {
      result.current.mutate(undefined as never);
    });

    await waitFor(() => {
      expect(mockToast).toHaveBeenCalledWith("Save failed", {
        action: expect.objectContaining({ label: "Retry" }),
      });
    });
  });

  it("retry action re-invokes mutate with original variables", async () => {
    const fn = vi.fn().mockRejectedValue(new Error("fail"));
    const { result } = renderHook(
      () =>
        useRetryableMutation<string, Error, string>({
          errorMessage: "Oops",
          mutationFn: fn,
        }),
      { wrapper: createWrapper() },
    );

    act(() => {
      result.current.mutate("my-var");
    });

    await waitFor(() => expect(mockToast).toHaveBeenCalled());

    const retryAction = mockToast.mock.calls[0][1].action;
    fn.mockResolvedValue("ok");

    act(() => {
      retryAction.onClick();
    });

    await waitFor(() => expect(fn).toHaveBeenCalledTimes(2));
    expect(fn).toHaveBeenLastCalledWith("my-var", expect.anything());
  });

  it("calls custom onError alongside toast", async () => {
    const fn = vi.fn().mockRejectedValue(new Error("fail"));
    const customOnError = vi.fn();
    const { result } = renderHook(
      () =>
        useRetryableMutation({
          errorMessage: "Error",
          mutationFn: fn,
          onError: customOnError,
        }),
      { wrapper: createWrapper() },
    );

    act(() => {
      result.current.mutate(undefined as never);
    });

    await waitFor(() => {
      expect(customOnError).toHaveBeenCalled();
      expect(mockToast).toHaveBeenCalled();
    });
  });

  it("calls onSuccess when mutation succeeds", async () => {
    const fn = vi.fn().mockResolvedValue("result");
    const onSuccess = vi.fn();
    const { result } = renderHook(
      () =>
        useRetryableMutation({
          errorMessage: "Error",
          mutationFn: fn,
          onSuccess,
        }),
      { wrapper: createWrapper() },
    );

    act(() => {
      result.current.mutate(undefined as never);
    });

    await waitFor(() => expect(onSuccess).toHaveBeenCalled());
    expect(mockToast).not.toHaveBeenCalled();
  });
});
