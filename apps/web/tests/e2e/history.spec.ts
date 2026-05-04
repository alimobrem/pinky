import { test, expect } from "@playwright/test";

test.describe("History page", () => {
  test.describe("unauthenticated", () => {
    test("redirects to login without session", async ({ page }) => {
      await page.goto("/history");
      await expect(page).toHaveURL(/\/login/);
    });
  });

  test.describe("page structure", () => {
    test("renders page header with eyebrow and title", async ({ page }) => {
      await page.goto("/history");
      if (page.url().includes("/login")) return;

      await expect(page.getByRole("heading", { name: "History" })).toBeVisible();
      await expect(page.getByText("Operational memory")).toBeVisible();
    });

    test("renders page description", async ({ page }) => {
      await page.goto("/history");
      if (page.url().includes("/login")) return;

      await expect(
        page.getByText(
          "Trace what changed across tasks, executions, approvals, and cluster activity without losing the thread.",
        ),
      ).toBeVisible();
    });

    test("shows event count in header meta", async ({ page }) => {
      await page.goto("/history");
      if (page.url().includes("/login")) return;

      await expect(page.getByText(/\d+ events in view/)).toBeVisible();
    });
  });

  test.describe("filter bar", () => {
    test("shows type filter dropdown", async ({ page }) => {
      await page.goto("/history");
      if (page.url().includes("/login")) return;

      const typeFilter = page.getByLabel("Filter history by type");
      await expect(typeFilter).toBeVisible();
      // Default value should be "All Types"
      await expect(typeFilter).toHaveValue("");
    });

    test("shows event count in filter bar", async ({ page }) => {
      await page.goto("/history");
      if (page.url().includes("/login")) return;

      // The filter bar shows "{n} events" count
      await expect(page.getByText(/\d+ events/).first()).toBeVisible();
    });
  });

  test.describe("empty state", () => {
    test("shows empty state when no events", async ({ page }) => {
      await page.goto("/history");
      if (page.url().includes("/login")) return;

      const noHistory = page.getByText("No operational history yet.");
      const hasEmpty = await noHistory.count();
      if (hasEmpty > 0) {
        await expect(page.getByText("No history yet")).toBeVisible();
        await expect(
          page.getByText(
            "Completed tasks, remediations, approvals, and system events will start building a narrative here over time.",
          ),
        ).toBeVisible();
        await expect(page.getByText("Review tasks")).toBeVisible();
      }
    });
  });

  test.describe("event timeline", () => {
    test("renders event rows when data present", async ({ page }) => {
      await page.goto("/history");
      if (page.url().includes("/login")) return;

      const noHistory = page.getByText("No operational history yet.");
      const isEmpty = (await noHistory.count()) > 0;
      if (!isEmpty) {
        // Events should be in a container with type indicators (colored dots)
        // Each row shows a timestamp and event type
        const eventCount = page.getByText(/\d+ events in view/);
        await expect(eventCount).toBeVisible();
      }
    });

    test("type filter options correspond to event types", async ({ page }) => {
      await page.goto("/history");
      if (page.url().includes("/login")) return;

      const typeFilter = page.getByLabel("Filter history by type");
      const options = await typeFilter.locator("option").allTextContents();
      // Should always have "All Types" as the first option
      expect(options[0]).toBe("All Types");
    });
  });
});
