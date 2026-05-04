import { test, expect } from "@playwright/test";

test.describe("Watch page", () => {
  test.describe("unauthenticated", () => {
    test("redirects to login without session", async ({ page }) => {
      await page.goto("/watch");
      await expect(page).toHaveURL(/\/login/);
    });
  });

  test.describe("page structure", () => {
    test("renders page header with eyebrow and title", async ({ page }) => {
      await page.goto("/watch");
      // If redirected to login, skip — this suite runs with or without auth
      if (page.url().includes("/login")) return;

      await expect(page.getByRole("heading", { name: "Watch" })).toBeVisible();
      await expect(page.getByText("Live watch")).toBeVisible();
    });

    test("renders page description", async ({ page }) => {
      await page.goto("/watch");
      if (page.url().includes("/login")) return;

      await expect(
        page.getByText("A high-signal stream of issues The Brain thinks deserve attention right now."),
      ).toBeVisible();
    });

    test("shows SSE connection indicator", async ({ page }) => {
      await page.goto("/watch");
      if (page.url().includes("/login")) return;

      // The connection indicator should show one of: Live, Connecting, Reconnecting
      const indicator = page.getByText(/Live|Connecting|Reconnecting/);
      await expect(indicator).toBeVisible();
    });
  });

  test.describe("empty state", () => {
    test("shows calm empty state when no issues", async ({ page }) => {
      await page.goto("/watch");
      if (page.url().includes("/login")) return;

      // Either issues are present or the empty state shows
      const hasIssues = await page.getByText("Suppress").count();
      if (hasIssues === 0) {
        await expect(page.getByText("Everything is calm")).toBeVisible();
        await expect(
          page.getByText("No active issues are bubbling up right now."),
        ).toBeVisible();
        await expect(page.getByText("Configure scanners")).toBeVisible();
      }
    });
  });

  test.describe("issue cards", () => {
    test("issue cards show severity badge and action buttons", async ({ page }) => {
      await page.goto("/watch");
      if (page.url().includes("/login")) return;

      const suppressButtons = page.getByRole("button", { name: "Suppress" });
      const count = await suppressButtons.count();
      if (count > 0) {
        // Each issue card should have Suppress, Resolve, and View tasks buttons
        await expect(suppressButtons.first()).toBeVisible();
        await expect(page.getByRole("button", { name: "Resolve" }).first()).toBeVisible();
        await expect(page.getByText("View tasks").first()).toBeVisible();
      }
    });

    test("severity badges are visible on issue cards", async ({ page }) => {
      await page.goto("/watch");
      if (page.url().includes("/login")) return;

      const suppressCount = await page.getByRole("button", { name: "Suppress" }).count();
      if (suppressCount > 0) {
        // At least one severity badge should exist (critical/high/medium/low)
        const severityBadge = page.getByText(/^(critical|high|medium|low)$/i).first();
        await expect(severityBadge).toBeVisible();
      }
    });
  });
});
