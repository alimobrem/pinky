import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { Badge } from "./badge";
import { StatusChip } from "./status-chip";
import { EmptyState } from "./empty-state";
import { Button } from "./button";
import { Card } from "./card";
import { Skeleton } from "./skeleton";

describe("Badge", () => {
  it("renders children", () => {
    render(<Badge>Critical</Badge>);
    expect(screen.getByText("Critical")).toBeInTheDocument();
  });

  it("defaults to default variant", () => {
    const { container } = render(<Badge>Test</Badge>);
    expect(container.firstChild).toHaveAttribute("data-variant", "default");
  });

  it("applies variant prop", () => {
    const { container } = render(<Badge variant="danger">Error</Badge>);
    expect(container.firstChild).toHaveAttribute("data-variant", "danger");
  });

  it("accepts all variant values", () => {
    const variants = ["default", "info", "success", "warning", "danger"] as const;
    for (const variant of variants) {
      const { container, unmount } = render(
        <Badge variant={variant}>{variant}</Badge>,
      );
      expect(container.firstChild).toHaveAttribute("data-variant", variant);
      unmount();
    }
  });
});

describe("StatusChip", () => {
  it("renders correct label for each status", () => {
    const cases = [
      ["ready", "Ready"],
      ["in_progress", "In Progress"],
      ["blocked", "Blocked"],
      ["waiting_for_approval", "Needs Approval"],
      ["done", "Done"],
    ] as const;
    for (const [status, label] of cases) {
      const { unmount } = render(<StatusChip status={status} />);
      expect(screen.getByText(label)).toBeInTheDocument();
      unmount();
    }
  });

  it("sets data-status attribute", () => {
    const { container } = render(<StatusChip status="blocked" />);
    expect(container.firstChild).toHaveAttribute("data-status", "blocked");
  });
});

describe("EmptyState", () => {
  it("renders message", () => {
    render(<EmptyState message="No items found" />);
    expect(screen.getByText("No items found")).toBeInTheDocument();
  });

  it("renders children when provided", () => {
    render(
      <EmptyState message="Empty">
        <button>Add</button>
      </EmptyState>,
    );
    expect(screen.getByRole("button", { name: "Add" })).toBeInTheDocument();
  });

  it("renders without children", () => {
    const { container } = render(<EmptyState message="Nothing here" />);
    expect(container.querySelector("p")).toHaveTextContent("Nothing here");
  });
});

describe("Button", () => {
  it("renders children", () => {
    render(<Button>Click me</Button>);
    expect(screen.getByRole("button", { name: "Click me" })).toBeInTheDocument();
  });

  it("defaults to primary variant and md size", () => {
    const { container } = render(<Button>Go</Button>);
    const btn = container.firstChild as HTMLElement;
    expect(btn).toHaveAttribute("data-variant", "primary");
    expect(btn).toHaveAttribute("data-size", "md");
  });

  it("applies variant and size props", () => {
    const { container } = render(
      <Button variant="danger" size="sm">
        Delete
      </Button>,
    );
    const btn = container.firstChild as HTMLElement;
    expect(btn).toHaveAttribute("data-variant", "danger");
    expect(btn).toHaveAttribute("data-size", "sm");
  });

  it("shows loading indicator when loading", () => {
    const { container } = render(<Button loading>Save</Button>);
    const btn = container.querySelector("button")!;
    expect(btn).toHaveTextContent("...");
    expect(btn).toBeDisabled();
  });

  it("is disabled when disabled prop is set", () => {
    const { container } = render(<Button disabled>Go</Button>);
    expect(container.querySelector("button")).toBeDisabled();
  });

  it("is disabled when loading even without disabled prop", () => {
    const { container } = render(<Button loading>Go</Button>);
    expect(container.querySelector("button")).toBeDisabled();
  });
});

describe("Card", () => {
  it("renders children", () => {
    render(<Card>Card content</Card>);
    expect(screen.getByText("Card content")).toBeInTheDocument();
  });

  it("passes through HTML attributes", () => {
    const { container } = render(
      <Card data-testid="my-card" className="custom">
        Content
      </Card>,
    );
    expect(container.firstChild).toHaveAttribute("data-testid", "my-card");
    expect(container.firstChild).toHaveClass("custom");
  });
});

describe("Skeleton", () => {
  it("renders with default dimensions", () => {
    const { container } = render(<Skeleton />);
    const el = container.firstChild as HTMLElement;
    expect(el.style.width).toBe("100%");
    expect(el.style.height).toBe("1rem");
  });

  it("accepts custom dimensions", () => {
    const { container } = render(<Skeleton width="200px" height="2rem" />);
    const el = container.firstChild as HTMLElement;
    expect(el.style.width).toBe("200px");
    expect(el.style.height).toBe("2rem");
  });

  it("has rounded class", () => {
    const { container } = render(<Skeleton />);
    expect(container.firstChild).toHaveClass("rounded");
  });
});
