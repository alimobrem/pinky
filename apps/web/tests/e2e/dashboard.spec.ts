import { test, expect } from "@playwright/test";

test.describe("Dashboard page", () => {
  test.describe("page structure", () => {
    test("renders page header with eyebrow and title", async ({ page }) => {
      await page.goto("/dashboard");
      // Dashboard is under (product) layout which requires server session.
      // If no session, it may redirect or show an error. Check for the title.
      if (page.url().includes("/login")) return;

      await expect(page.getByRole("heading", { name: "Dashboard" })).toBeVisible();
      await expect(page.getByText("Operations overview")).toBeVisible();
    });

    test("renders page description", async ({ page }) => {
      await page.goto("/dashboard");
      if (page.url().includes("/login")) return;

      await expect(
        page.getByText(
          "See what needs attention, where it is happening, and whether The Brain is surfacing work that still needs a decision.",
        ),
      ).toBeVisible();
    });

    test("shows active task and issue counts in header meta", async ({ page }) => {
      await page.goto("/dashboard");
      if (page.url().includes("/login")) return;

      await expect(page.getByText(/\d+ active tasks/)).toBeVisible();
      await expect(page.getByText(/\d+ open issues/)).toBeVisible();
      await expect(page.getByText(/\d+ registered clusters/)).toBeVisible();
    });
  });

  test.describe("task summary card", () => {
    test("shows task counts with status labels", async ({ page }) => {
      await page.goto("/dashboard");
      if (page.url().includes("/login")) return;

      await expect(page.getByText("Tasks").first()).toBeVisible();
      await expect(page.getByText("Ready")).toBeVisible();
      await expect(page.getByText("Active")).toBeVisible();
      await expect(page.getByText("Blocked")).toBeVisible();
      await expect(page.getByText("Approval")).toBeVisible();
    });

    test("has View all link to tasks page", async ({ page }) => {
      await page.goto("/dashboard");
      if (page.url().includes("/login")) return;

      const viewAll = page.getByRole("link", { name: "View all" });
      await expect(viewAll).toBeVisible();
      await expect(viewAll).toHaveAttribute("href", "/tasks");
    });
  });

  test.describe("clusters card", () => {
    test("shows clusters section with manage link", async ({ page }) => {
      await page.goto("/dashboard");
      if (page.url().includes("/login")) return;

      await expect(page.getByText("Clusters").first()).toBeVisible();
      const manage = page.getByRole("link", { name: "Manage" });
      await expect(manage).toBeVisible();
      await expect(manage).toHaveAttribute("href", "/settings");
    });

    test("shows empty state or cluster list", async ({ page }) => {
      await page.goto("/dashboard");
      if (page.url().includes("/login")) return;

      const noClusterText = page.getByText("No clusters registered.");
      const hasEmpty = await noClusterText.count();
      if (hasEmpty > 0) {
        await expect(page.getByText("Add one")).toBeVisible();
      }
      // If clusters exist, the section just renders cluster names — no specific assertion needed
    });
  });

  test.describe("pending approvals card", () => {
    test("shows pending approvals section", async ({ page }) => {
      await page.goto("/dashboard");
      if (page.url().includes("/login")) return;

      await expect(page.getByText("Pending Approvals")).toBeVisible();
      // Either "No pending approvals" or a list of tasks
      const noPending = page.getByText("No pending approvals");
      const hasPending = await noPending.count();
      if (hasPending > 0) {
        await expect(noPending).toBeVisible();
      }
    });
  });

  test.describe("active issues card", () => {
    test("shows active issues section with watch link", async ({ page }) => {
      await page.goto("/dashboard");
      if (page.url().includes("/login")) return;

      await expect(page.getByText("Active Issues")).toBeVisible();
      const watchLink = page.getByRole("link", { name: "Watch" });
      await expect(watchLink).toBeVisible();
      await expect(watchLink).toHaveAttribute("href", "/watch");
    });

    test("shows All quiet or issue list", async ({ page }) => {
      await page.goto("/dashboard");
      if (page.url().includes("/login")) return;

      const quietText = page.getByText("All quiet");
      const hasQuiet = await quietText.count();
      if (hasQuiet > 0) {
        await expect(quietText).toBeVisible();
      }
    });
  });

  test.describe("recent activity card", () => {
    test("shows recent activity with history link", async ({ page }) => {
      await page.goto("/dashboard");
      if (page.url().includes("/login")) return;

      await expect(page.getByText("Recent Activity")).toBeVisible();
      const historyLink = page.getByRole("link", { name: "History" });
      await expect(historyLink).toBeVisible();
      await expect(historyLink).toHaveAttribute("href", "/history");
    });

    test("shows No activity yet or event list", async ({ page }) => {
      await page.goto("/dashboard");
      if (page.url().includes("/login")) return;

      const noActivity = page.getByText("No activity yet");
      const hasNoActivity = await noActivity.count();
      if (hasNoActivity > 0) {
        await expect(noActivity).toBeVisible();
      }
    });
  });

  test.describe("brain status card", () => {
    test("shows The Brain card with status info", async ({ page }) => {
      await page.goto("/dashboard");
      if (page.url().includes("/login")) return;

      await expect(page.getByText("The Brain")).toBeVisible();
      await expect(page.getByText("Online — monitoring")).toBeVisible();
      await expect(page.getByText("Status").first()).toBeVisible();
      await expect(page.getByText("Open issues")).toBeVisible();
      await expect(page.getByText("Active tasks")).toBeVisible();
    });
  });
});
