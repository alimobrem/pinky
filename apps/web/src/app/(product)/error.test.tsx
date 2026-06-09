import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import ProductError from "./error";

describe("ProductError", () => {
  const testError = new Error("Connection refused");
  const mockReset = vi.fn();

  beforeEach(() => {
    vi.spyOn(console, "error").mockImplementation(() => {});
    mockReset.mockReset();
  });

  it("renders the error message", () => {
    render(<ProductError error={testError} reset={mockReset} />);
    expect(
      screen.getAllByText("Connection refused").length,
    ).toBeGreaterThanOrEqual(1);
    expect(
      screen.getAllByText("Something went wrong").length,
    ).toBeGreaterThanOrEqual(1);
  });

  it("calls reset when Retry button is clicked", () => {
    render(<ProductError error={testError} reset={mockReset} />);
    const retryButtons = screen.getAllByRole("button", { name: /retry/i });
    fireEvent.click(retryButtons[0]);
    expect(mockReset).toHaveBeenCalledOnce();
  });

  it("navigates to /dashboard when Dashboard button is clicked", () => {
    let capturedHref = "";
    Object.defineProperty(window, "location", {
      value: {
        ...window.location,
        get href() {
          return capturedHref;
        },
        set href(v: string) {
          capturedHref = v;
        },
      },
      writable: true,
      configurable: true,
    });

    render(<ProductError error={testError} reset={mockReset} />);
    const dashButtons = screen.getAllByRole("button", { name: /dashboard/i });
    fireEvent.click(dashButtons[0]);
    expect(capturedHref).toBe("/dashboard");
  });

  it("renders descriptive subtitle text", () => {
    render(<ProductError error={testError} reset={mockReset} />);
    expect(
      screen.getAllByText(/unexpected error occurred/i).length,
    ).toBeGreaterThanOrEqual(1);
  });
});
