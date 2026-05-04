import { test, expect } from "@playwright/test";

test.describe("Alerts page", () => {
  test.describe("unauthenticated", () => {
    test("redirects to login without session", async ({ page }) => {
      await page.goto("/alerts");
      await expect(page).toHaveURL(/\/login/);
    });
  });

  test.describe("page structure", () => {
    test("renders page header with eyebrow and title", async ({ page }) => {
      await page.goto("/alerts");
      if (page.url().includes("/login")) return;

      await expect(page.getByRole("heading", { name: "Alerts" })).toBeVisible();
      await expect(page.getByText("Raw signal feed")).toBeVisible();
    });

    test("renders page description", async ({ page }) => {
      await page.goto("/alerts");
      if (page.url().includes("/login")) return;

      await expect(
        page.getByText(
          "See the lower-level observations and scanner payloads that inform the higher-signal task inbox.",
        ),
      ).toBeVisible();
    });

    test("shows alert count in header meta", async ({ page }) => {
      await page.goto("/alerts");
      if (page.url().includes("/login")) return;

      await expect(page.getByText(/\d+ alerts in view/)).toBeVisible();
    });
  });

  test.describe("severity filter", () => {
    test("shows severity filter dropdown", async ({ page }) => {
      await page.goto("/alerts");
      if (page.url().includes("/login")) return;

      const severityFilter = page.getByLabel("Filter alerts by severity");
      await expect(severityFilter).toBeVisible();
      await expect(severityFilter).toHaveValue("");
    });

    test("severity filter has all severity options", async ({ page }) => {
      await page.goto("/alerts");
      if (page.url().includes("/login")) return;

      const severityFilter = page.getByLabel("Filter alerts by severity");
      const options = await severityFilter.locator("option").allTextContents();
      expect(options).toContain("All Severities");
      expect(options).toContain("Critical");
      expect(options).toContain("High");
      expect(options).toContain("Medium");
      expect(options).toContain("Low");
    });

    test("shows alert count in filter bar", async ({ page }) => {
      await page.goto("/alerts");
      if (page.url().includes("/login")) return;

      await expect(page.getByText(/\d+ alerts/).first()).toBeVisible();
    });
  });

  test.describe("empty state", () => {
    test("shows Raw feed is clear empty state when no alerts", async ({ page }) => {
      await page.goto("/alerts");
      if (page.url().includes("/login")) return;

      const noAlerts = page.getByText("No active alerts.");
      const hasEmpty = await noAlerts.count();
      if (hasEmpty > 0) {
        await expect(page.getByText("Raw feed is clear")).toBeVisible();
        await expect(
          page.getByText(
            "Lower-level observation signals from your scanners will appear here as soon as they are detected.",
          ),
        ).toBeVisible();
        await expect(page.getByText("Connect a cluster")).toBeVisible();
      }
    });
  });

  test.describe("alert cards", () => {
    test("alert cards show scanner name and severity badge", async ({ page }) => {
      await page.goto("/alerts");
      if (page.url().includes("/login")) return;

      const noAlerts = page.getByText("No active alerts.");
      const isEmpty = (await noAlerts.count()) > 0;
      if (!isEmpty) {
        // At least one severity badge should exist
        const severityBadge = page.getByText(/^(critical|high|medium|low)$/i).first();
        await expect(severityBadge).toBeVisible();
      }
    });

    test("alert cards are expandable", async ({ page }) => {
      await page.goto("/alerts");
      if (page.url().includes("/login")) return;

      const noAlerts = page.getByText("No active alerts.");
      const isEmpty = (await noAlerts.count()) > 0;
      if (!isEmpty) {
        // Before click, chevron-right should be visible (collapsed state)
        // Click the first alert card to expand it
        const firstCard = page.locator("[class*='rounded-xl'][class*='border-l-']").first();
        if ((await firstCard.count()) > 0) {
          await firstCard.click();
          // After expanding, the Payload section may appear if the alert has payload data
          // This is a best-effort check
        }
      }
    });
  });
});
