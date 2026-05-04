import { test, expect } from "@playwright/test";

test.describe("Task detail page", () => {
  test.describe("unauthenticated", () => {
    test("redirects to login without session", async ({ page }) => {
      await page.goto("/tasks/fake-id-123");
      await expect(page).toHaveURL(/\/login/);
    });
  });

  test.describe("navigation", () => {
    test("shows Back to Tasks button", async ({ page }) => {
      await page.goto("/tasks");
      if (page.url().includes("/login")) return;

      // Navigate to first task if available
      const firstTask = page.locator("a[href^='/tasks/']").first();
      if ((await firstTask.count()) === 0) return;

      await firstTask.click();
      await expect(page.getByText("Back to Tasks")).toBeVisible();
    });

    test("Back to Tasks navigates to task list", async ({ page }) => {
      await page.goto("/tasks");
      if (page.url().includes("/login")) return;

      const firstTask = page.locator("a[href^='/tasks/']").first();
      if ((await firstTask.count()) === 0) return;

      await firstTask.click();
      await expect(page.getByText("Back to Tasks")).toBeVisible();

      await page.getByText("Back to Tasks").click();
      await expect(page).toHaveURL(/\/tasks$/);
    });
  });

  test.describe("page header", () => {
    test("shows eyebrow, title, and status badges", async ({ page }) => {
      await page.goto("/tasks");
      if (page.url().includes("/login")) return;

      const firstTask = page.locator("a[href^='/tasks/']").first();
      if ((await firstTask.count()) === 0) return;

      await firstTask.click();
      await expect(page.getByText("Investigation workspace")).toBeVisible();
      // Task title should be visible as h1
      await expect(page.locator("h1")).toBeVisible();
      // Status and priority badges
      const badges = page.locator("[class*='badge'], [class*='Badge']");
      expect(await badges.count()).toBeGreaterThan(0);
    });
  });

  test.describe("situation summary section", () => {
    test("shows situation summary with Why now", async ({ page }) => {
      await page.goto("/tasks");
      if (page.url().includes("/login")) return;

      const firstTask = page.locator("a[href^='/tasks/']").first();
      if ((await firstTask.count()) === 0) return;

      await firstTask.click();
      await expect(page.getByText("Situation summary")).toBeVisible();
      await expect(page.getByText("Why now")).toBeVisible();
      await expect(page.getByText("Status").first()).toBeVisible();
      await expect(page.getByText("Priority").first()).toBeVisible();
    });
  });

  test.describe("investigation section", () => {
    test("shows investigation or no-investigation state", async ({ page }) => {
      await page.goto("/tasks");
      if (page.url().includes("/login")) return;

      const firstTask = page.locator("a[href^='/tasks/']").first();
      if ((await firstTask.count()) === 0) return;

      await firstTask.click();

      // Either shows investigation content or the "No investigation data yet" state
      const noInvestigation = page.getByText("No investigation data yet.");
      const hasNoInv = await noInvestigation.count();
      if (hasNoInv > 0) {
        await expect(
          page.getByText("Trigger an investigation to have The Brain analyze this issue."),
        ).toBeVisible();
      } else {
        // Investigation section should have the heading
        await expect(page.getByText("Investigation")).toBeVisible();
      }
    });
  });

  test.describe("brain recommendations sidebar", () => {
    test("shows The Brain recommends panel", async ({ page }) => {
      await page.goto("/tasks");
      if (page.url().includes("/login")) return;

      const firstTask = page.locator("a[href^='/tasks/']").first();
      if ((await firstTask.count()) === 0) return;

      await firstTask.click();
      await expect(page.getByText("The Brain recommends")).toBeVisible();
    });

    test("shows Next moves section with investigation trigger", async ({ page }) => {
      await page.goto("/tasks");
      if (page.url().includes("/login")) return;

      const firstTask = page.locator("a[href^='/tasks/']").first();
      if ((await firstTask.count()) === 0) return;

      await firstTask.click();
      await expect(page.getByText("Next moves")).toBeVisible();

      // Should show either "Run Brain Investigation" or "Re-investigate"
      const runInvestigation = page.getByText(/Run Brain Investigation|Re-investigate/);
      await expect(runInvestigation).toBeVisible();
    });
  });

  test.describe("execution timeline section", () => {
    test("shows execution timeline section", async ({ page }) => {
      await page.goto("/tasks");
      if (page.url().includes("/login")) return;

      const firstTask = page.locator("a[href^='/tasks/']").first();
      if ((await firstTask.count()) === 0) return;

      await firstTask.click();
      await expect(page.getByText("Execution timeline")).toBeVisible();

      // Either "No execution events yet." or a list of events
      const noEvents = page.getByText("No execution events yet.");
      const hasNoEvents = await noEvents.count();
      if (hasNoEvents > 0) {
        await expect(noEvents).toBeVisible();
      }
    });
  });

  test.describe("task not found", () => {
    test("shows not found message for invalid task ID", async ({ page }) => {
      await page.goto("/tasks");
      if (page.url().includes("/login")) return;

      // Navigate directly to a nonexistent task
      await page.goto("/tasks/00000000-0000-0000-0000-000000000000");
      // Should show "Task not found." after loading
      await expect(page.getByText("Task not found.")).toBeVisible({ timeout: 10000 });
    });
  });
});
