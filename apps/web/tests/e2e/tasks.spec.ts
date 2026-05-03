import { test, expect } from "@playwright/test";

test("tasks page shows summary strip", async ({ page }) => {
  await page.goto("/tasks");
  await expect(page.locator("text=READY")).toBeVisible();
  await expect(page.locator("text=IN PROGRESS")).toBeVisible();
  await expect(page.locator("text=BLOCKED")).toBeVisible();
  await expect(page.locator("text=NEEDS APPROVAL")).toBeVisible();
});

test("tasks page shows empty state when no data", async ({ page }) => {
  await page.goto("/tasks");
  // Either shows tasks or the empty state
  const hasItems = await page.locator("[data-status]").count();
  if (hasItems === 0) {
    await expect(page.locator("text=Nothing needs your attention")).toBeVisible();
  }
});

test("task detail page loads when clicked", async ({ page }) => {
  await page.goto("/tasks");
  // If there are task cards, click the first one
  const firstCard = page.locator("a[href^='/tasks/']").first();
  if (await firstCard.isVisible()) {
    await firstCard.click();
    await expect(page.locator("text=Back to Tasks")).toBeVisible();
    await expect(page.locator("text=SUMMARY")).toBeVisible();
  }
});
