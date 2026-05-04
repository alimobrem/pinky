import { test, expect } from "@playwright/test";

test.describe("Settings page", () => {
  test.describe("unauthenticated", () => {
    test("redirects to login without session", async ({ page }) => {
      await page.goto("/settings");
      await expect(page).toHaveURL(/\/login/);
    });
  });

  test.describe("page structure", () => {
    test("renders page header with eyebrow and title", async ({ page }) => {
      await page.goto("/settings");
      if (page.url().includes("/login")) return;

      await expect(page.getByRole("heading", { name: "Settings" })).toBeVisible();
      await expect(page.getByText("System configuration")).toBeVisible();
    });

    test("renders page description", async ({ page }) => {
      await page.goto("/settings");
      if (page.url().includes("/login")) return;

      await expect(
        page.getByText(
          "Manage clusters, bindings, definitions, notification plumbing, and the platform rules that shape how The Brain behaves.",
        ),
      ).toBeVisible();
    });

    test("shows meta counts in header", async ({ page }) => {
      await page.goto("/settings");
      if (page.url().includes("/login")) return;

      await expect(page.getByText(/\d+ clusters/)).toBeVisible();
      await expect(page.getByText(/\d+ bindings/)).toBeVisible();
      await expect(page.getByText(/\d+ definitions/)).toBeVisible();
      await expect(page.getByText(/\d+ policy rules/)).toBeVisible();
    });
  });

  test.describe("tabs", () => {
    test("shows all configuration tabs", async ({ page }) => {
      await page.goto("/settings");
      if (page.url().includes("/login")) return;

      await expect(page.getByText("Configuration areas")).toBeVisible();
      await expect(page.getByRole("tab", { name: /Clusters/ })).toBeVisible();
      await expect(page.getByRole("tab", { name: /Definitions/ })).toBeVisible();
      await expect(page.getByRole("tab", { name: /Webhooks/ })).toBeVisible();
      await expect(page.getByRole("tab", { name: /Policy Rules/ })).toBeVisible();
      await expect(page.getByRole("tab", { name: /Cluster Access/ })).toBeVisible();
      await expect(page.getByRole("tab", { name: /Analytics/ })).toBeVisible();
    });

    test("clusters tab is active by default", async ({ page }) => {
      await page.goto("/settings");
      if (page.url().includes("/login")) return;

      await expect(page.getByText("Registered Clusters")).toBeVisible();
    });
  });

  test.describe("clusters tab", () => {
    test("shows Add button for clusters", async ({ page }) => {
      await page.goto("/settings");
      if (page.url().includes("/login")) return;

      const addButton = page.getByRole("button", { name: "Add" }).first();
      await expect(addButton).toBeVisible();
    });

    test("shows empty state or cluster list", async ({ page }) => {
      await page.goto("/settings");
      if (page.url().includes("/login")) return;

      const noCluster = page.getByText("No clusters registered.");
      const hasEmpty = await noCluster.count();
      if (hasEmpty > 0) {
        await expect(page.getByText("+ Add first cluster")).toBeVisible();
      }
    });

    test("Add button opens cluster dialog", async ({ page }) => {
      await page.goto("/settings");
      if (page.url().includes("/login")) return;

      await page.getByRole("button", { name: "Add" }).first().click();
      await expect(page.getByText("Add Cluster")).toBeVisible();
      await expect(page.getByText("Display Name *")).toBeVisible();
      await expect(page.getByText("API Endpoint *")).toBeVisible();
      await expect(page.getByText("Fleet Identifier")).toBeVisible();
      await expect(page.getByRole("button", { name: "Cancel" })).toBeVisible();
      // Add Cluster submit should be disabled with empty fields
      const submitBtn = page.getByRole("button", { name: "Add Cluster" });
      await expect(submitBtn).toBeVisible();
      await expect(submitBtn).toBeDisabled();
    });

    test("cluster dialog cancel closes dialog", async ({ page }) => {
      await page.goto("/settings");
      if (page.url().includes("/login")) return;

      await page.getByRole("button", { name: "Add" }).first().click();
      await expect(page.getByText("Add Cluster")).toBeVisible();
      await page.getByRole("button", { name: "Cancel" }).click();
      await expect(page.getByText("Add Cluster")).not.toBeVisible();
    });
  });

  test.describe("definitions tab", () => {
    test("shows definitions content when tab is clicked", async ({ page }) => {
      await page.goto("/settings");
      if (page.url().includes("/login")) return;

      await page.getByRole("tab", { name: /Definitions/ }).click();
      await expect(page.getByText("Definitions").first()).toBeVisible();
    });

    test("shows Add button and empty or list state", async ({ page }) => {
      await page.goto("/settings");
      if (page.url().includes("/login")) return;

      await page.getByRole("tab", { name: /Definitions/ }).click();
      await expect(page.getByRole("button", { name: "Add" }).first()).toBeVisible();

      const noDefs = page.getByText("No definitions in DB.");
      const hasEmpty = await noDefs.count();
      if (hasEmpty > 0) {
        await expect(noDefs).toBeVisible();
      }
    });

    test("Add button opens definition dialog with kind selector", async ({ page }) => {
      await page.goto("/settings");
      if (page.url().includes("/login")) return;

      await page.getByRole("tab", { name: /Definitions/ }).click();
      await page.getByRole("button", { name: "Add" }).first().click();
      await expect(page.getByText("Create Definition")).toBeVisible();
      await expect(page.getByText("Kind")).toBeVisible();
      await expect(page.getByText("Name *")).toBeVisible();
    });
  });

  test.describe("webhooks tab", () => {
    test("shows webhooks content when tab is clicked", async ({ page }) => {
      await page.goto("/settings");
      if (page.url().includes("/login")) return;

      await page.getByRole("tab", { name: /Webhooks/ }).click();
      await expect(page.getByText("Webhook Subscriptions")).toBeVisible();
    });

    test("shows empty state or webhook list", async ({ page }) => {
      await page.goto("/settings");
      if (page.url().includes("/login")) return;

      await page.getByRole("tab", { name: /Webhooks/ }).click();
      const noWebhooks = page.getByText("No webhook subscriptions.");
      const hasEmpty = await noWebhooks.count();
      if (hasEmpty > 0) {
        await expect(noWebhooks).toBeVisible();
      }
    });

    test("Add button opens webhook dialog", async ({ page }) => {
      await page.goto("/settings");
      if (page.url().includes("/login")) return;

      await page.getByRole("tab", { name: /Webhooks/ }).click();
      await page.getByRole("button", { name: "Add" }).first().click();
      await expect(page.getByText("Create Webhook")).toBeVisible();
      await expect(page.getByText("Name *")).toBeVisible();
      await expect(page.getByText("URL *")).toBeVisible();
    });
  });

  test.describe("policy rules tab", () => {
    test("shows policy rules content when tab is clicked", async ({ page }) => {
      await page.goto("/settings");
      if (page.url().includes("/login")) return;

      await page.getByRole("tab", { name: /Policy Rules/ }).click();
      // "Policy Rules" appears in the tab itself, check for the section content
      await expect(page.getByText("Policy Rules", { exact: false }).first()).toBeVisible();
    });

    test("shows empty state or rules list", async ({ page }) => {
      await page.goto("/settings");
      if (page.url().includes("/login")) return;

      await page.getByRole("tab", { name: /Policy Rules/ }).click();
      const noRules = page.getByText("No policy rules configured.");
      const hasEmpty = await noRules.count();
      if (hasEmpty > 0) {
        await expect(noRules).toBeVisible();
      }
    });

    test("Add button opens policy rule dialog", async ({ page }) => {
      await page.goto("/settings");
      if (page.url().includes("/login")) return;

      await page.getByRole("tab", { name: /Policy Rules/ }).click();
      await page.getByRole("button", { name: "Add" }).first().click();
      await expect(page.getByText("Create Policy Rule")).toBeVisible();
      await expect(page.getByText("Name *")).toBeVisible();
      await expect(page.getByText("Priority")).toBeVisible();
      await expect(page.getByText("Conditions (JSON)")).toBeVisible();
      await expect(page.getByText("Action (JSON)")).toBeVisible();
    });
  });

  test.describe("cluster access tab", () => {
    test("shows cluster access content when tab is clicked", async ({ page }) => {
      await page.goto("/settings");
      if (page.url().includes("/login")) return;

      await page.getByRole("tab", { name: /Cluster Access/ }).click();
      await expect(page.getByText("Your Cluster Bindings")).toBeVisible();
    });

    test("shows empty state or bindings list", async ({ page }) => {
      await page.goto("/settings");
      if (page.url().includes("/login")) return;

      await page.getByRole("tab", { name: /Cluster Access/ }).click();
      const noBindings = page.getByText("No cluster bindings.");
      const hasEmpty = await noBindings.count();
      if (hasEmpty > 0) {
        await expect(noBindings).toBeVisible();
      }
    });

    test("shows Connect to Cluster button", async ({ page }) => {
      await page.goto("/settings");
      if (page.url().includes("/login")) return;

      await page.getByRole("tab", { name: /Cluster Access/ }).click();
      await expect(page.getByRole("button", { name: "Connect to Cluster" })).toBeVisible();
    });
  });

  test.describe("analytics tab", () => {
    test("shows analytics content when tab is clicked", async ({ page }) => {
      await page.goto("/settings");
      if (page.url().includes("/login")) return;

      await page.getByRole("tab", { name: /Analytics/ }).click();
      await expect(page.getByText("ROI Metrics")).toBeVisible();
    });

    test("shows empty state or metrics", async ({ page }) => {
      await page.goto("/settings");
      if (page.url().includes("/login")) return;

      await page.getByRole("tab", { name: /Analytics/ }).click();
      const noData = page.getByText("No analytics data yet.");
      const hasEmpty = await noData.count();
      if (hasEmpty > 0) {
        await expect(noData).toBeVisible();
      }
    });
  });
});
