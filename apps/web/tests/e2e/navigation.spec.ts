import { test, expect } from "@playwright/test";

test("login page renders with brand", async ({ page }) => {
  await page.goto("/login");
  await expect(page.locator("text=PINKY")).toBeVisible();
  await expect(page.locator("text=Sign in with OpenShift")).toBeVisible();
  await expect(page.locator("text=Sign in with OIDC")).toBeVisible();
  await expect(page.locator("text=Powered by The Brain")).toBeVisible();
});

test("tasks page loads", async ({ page }) => {
  await page.goto("/tasks");
  await expect(page.locator("text=Tasks")).toBeVisible();
});

test("watch page loads", async ({ page }) => {
  await page.goto("/watch");
  await expect(page.locator("text=Watch")).toBeVisible();
});

test("history page loads", async ({ page }) => {
  await page.goto("/history");
  await expect(page.locator("text=History")).toBeVisible();
});

test("alerts page loads", async ({ page }) => {
  await page.goto("/alerts");
  await expect(page.locator("text=Alerts")).toBeVisible();
});

test("settings page loads", async ({ page }) => {
  await page.goto("/settings");
  await expect(page.locator("text=Settings")).toBeVisible();
});

test("nav rail has all items", async ({ page }) => {
  await page.goto("/tasks");
  await expect(page.locator("text=Tasks")).toBeVisible();
  await expect(page.locator("text=Watch")).toBeVisible();
  await expect(page.locator("text=History")).toBeVisible();
  await expect(page.locator("text=Alerts")).toBeVisible();
  await expect(page.locator("text=Settings")).toBeVisible();
});

test("root redirects to tasks", async ({ page }) => {
  await page.goto("/");
  await page.waitForURL("/tasks");
  await expect(page).toHaveURL("/tasks");
});
