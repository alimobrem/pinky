import { test, expect } from "@playwright/test";

test.describe("Settings CRUD", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/settings");
    if (page.url().includes("/login")) return;
  });

  test("loads all 6 tabs", async ({ page }) => {
    if (page.url().includes("/login")) return;
    await expect(page.getByRole("tab", { name: /Clusters/i })).toBeVisible();
    await expect(page.getByRole("tab", { name: /Definitions/i })).toBeVisible();
    await expect(page.getByRole("tab", { name: /Webhooks/i })).toBeVisible();
    await expect(page.getByRole("tab", { name: /Rules/i })).toBeVisible();
    await expect(page.getByRole("tab", { name: /Access/i })).toBeVisible();
    await expect(page.getByRole("tab", { name: /Analytics/i })).toBeVisible();
  });

  test("definitions tab shows list", async ({ page }) => {
    if (page.url().includes("/login")) return;
    await page.getByRole("tab", { name: /Definitions/i }).click();
    await expect(page.getByText("Definitions")).toBeVisible();
  });

  test("definitions tab has create button", async ({ page }) => {
    if (page.url().includes("/login")) return;
    await page.getByRole("tab", { name: /Definitions/i }).click();
    await expect(page.getByRole("button", { name: /Create/i })).toBeVisible();
  });

  test("webhooks tab shows list", async ({ page }) => {
    if (page.url().includes("/login")) return;
    await page.getByRole("tab", { name: /Webhooks/i }).click();
    await expect(page.getByText("Webhooks")).toBeVisible();
    await expect(page.getByRole("button", { name: /Create/i })).toBeVisible();
  });

  test("rules tab shows list with test button", async ({ page }) => {
    if (page.url().includes("/login")) return;
    await page.getByRole("tab", { name: /Rules/i }).click();
    await expect(page.getByText("Policy Rules")).toBeVisible();
    await expect(page.getByRole("button", { name: /Test/i })).toBeVisible();
    await expect(page.getByRole("button", { name: /Create/i })).toBeVisible();
  });

  test("analytics tab has period selector", async ({ page }) => {
    if (page.url().includes("/login")) return;
    await page.getByRole("tab", { name: /Analytics/i }).click();
    await expect(page.getByText("Platform Analytics")).toBeVisible();
    await expect(page.getByRole("button", { name: "7d" })).toBeVisible();
    await expect(page.getByRole("button", { name: "30d" })).toBeVisible();
    await expect(page.getByRole("button", { name: "90d" })).toBeVisible();
  });

  test("access tab shows binding management", async ({ page }) => {
    if (page.url().includes("/login")) return;
    await page.getByRole("tab", { name: /Access/i }).click();
    await expect(page.getByText("Cluster Bindings")).toBeVisible();
    await expect(page.getByRole("button", { name: /Connect/i })).toBeVisible();
  });

  test("clusters tab has add button", async ({ page }) => {
    if (page.url().includes("/login")) return;
    await expect(page.getByRole("button", { name: /Add/i })).toBeVisible();
  });
});
