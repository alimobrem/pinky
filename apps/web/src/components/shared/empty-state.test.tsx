import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { EmptyState } from "./empty-state";
import { AlertCircle } from "lucide-react";

describe("EmptyState", () => {
  it("renders title text", () => {
    render(<EmptyState title="No items found" />);
    expect(screen.getByText("No items found")).toBeInTheDocument();
  });

  it("renders description when provided", () => {
    render(
      <EmptyState title="Empty" description="Try creating a new item" />,
    );
    expect(screen.getByText("Try creating a new item")).toBeInTheDocument();
  });

  it("does not render description when omitted", () => {
    const { container } = render(<EmptyState title="Empty" />);
    const paragraphs = container.querySelectorAll("p");
    expect(paragraphs).toHaveLength(1);
    expect(paragraphs[0].textContent).toBe("Empty");
  });

  it("renders action when provided", () => {
    render(
      <EmptyState
        title="Empty"
        action={<button type="button">Create</button>}
      />,
    );
    expect(
      screen.getByRole("button", { name: "Create" }),
    ).toBeInTheDocument();
  });

  it("uses default Inbox icon when none specified", () => {
    const { container } = render(<EmptyState title="Empty" />);
    const svg = container.querySelector("svg");
    expect(svg).toBeInTheDocument();
  });

  it("uses custom icon when provided", () => {
    const { container } = render(
      <EmptyState title="Error" icon={AlertCircle} />,
    );
    const svg = container.querySelector("svg");
    expect(svg).toBeInTheDocument();
  });
});
