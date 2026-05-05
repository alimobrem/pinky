import { test, expect } from "@playwright/test";

test.describe("Real-time updates", () => {
  test("dashboard renders without errors", async ({ page }) => {
    await page.goto("/dashboard");
    if (page.url().includes("/login")) return;
    await expect(page.getByText("Dashboard")).toBeVisible();
    await expect(page.getByText("Fleet overview")).toBeVisible();
    const errors = await page.evaluate(() =>
      (window as unknown as { __console_errors?: string[] }).__console_errors ?? []
    );
    expect(errors).toHaveLength(0);
  });

  test("tasks page renders with table or cards", async ({ page }) => {
    await page.goto("/tasks");
    if (page.url().includes("/login")) return;
    await expect(page.getByText("Tasks")).toBeVisible();
    await expect(page.getByText(/Work items surfaced/)).toBeVisible();
  });

  test("watch page shows connection status", async ({ page }) => {
    await page.goto("/watch");
    if (page.url().includes("/login")) return;
    await expect(page.getByText("Watch")).toBeVisible();
    const hasStatus = await page.getByText(/Live|Disconnected|Reconnecting/).isVisible().catch(() => false);
    expect(hasStatus).toBeTruthy();
  });
});
