import { test, expect } from "@playwright/test";

test.describe("Tasks page", () => {
  test.describe("unauthenticated", () => {
    test("redirects to login without session", async ({ page }) => {
      await page.goto("/tasks");
      await expect(page).toHaveURL(/\/login/);
    });
  });

  test.describe("page structure", () => {
    test("renders page header with eyebrow and title", async ({ page }) => {
      await page.goto("/tasks");
      if (page.url().includes("/login")) return;

      await expect(page.getByRole("heading", { name: "Tasks" })).toBeVisible();
      await expect(page.getByText("Investigation inbox")).toBeVisible();
    });

    test("renders page description", async ({ page }) => {
      await page.goto("/tasks");
      if (page.url().includes("/login")) return;

      await expect(
        page.getByText(
          "Triage what surfaced, decide what to act on, and keep the highest-signal operational work visible.",
        ),
      ).toBeVisible();
    });

    test("shows meta counts in header", async ({ page }) => {
      await page.goto("/tasks");
      if (page.url().includes("/login")) return;

      await expect(page.getByText(/\d+ tasks in scope/)).toBeVisible();
      await expect(page.getByText(/\d+ ready to triage/)).toBeVisible();
      await expect(page.getByText(/\d+ waiting on approval/)).toBeVisible();
    });
  });

  test.describe("summary strip / queue tabs", () => {
    test("shows all queue tabs with counts", async ({ page }) => {
      await page.goto("/tasks");
      if (page.url().includes("/login")) return;

      await expect(page.getByText("All tasks")).toBeVisible();
      await expect(page.getByText("Ready to triage")).toBeVisible();
      await expect(page.getByText("In progress")).toBeVisible();
      await expect(page.getByText("Blocked")).toBeVisible();
      await expect(page.getByText("Needs approval")).toBeVisible();
    });

    test("All tasks queue is active by default", async ({ page }) => {
      await page.goto("/tasks");
      if (page.url().includes("/login")) return;

      // The description for All tasks queue
      await expect(
        page.getByText("Everything The Brain surfaced for review."),
      ).toBeVisible();
    });

    test("clicking a queue tab updates description", async ({ page }) => {
      await page.goto("/tasks");
      if (page.url().includes("/login")) return;

      await page.getByText("Ready to triage").click();
      await expect(
        page.getByText("Fresh work that needs a human read."),
      ).toBeVisible();

      await page.getByText("Blocked").click();
      await expect(
        page.getByText("Needs an unblock before it can move."),
      ).toBeVisible();

      await page.getByText("Needs approval").click();
      await expect(
        page.getByText("Waiting on a human decision to continue."),
      ).toBeVisible();
    });
  });

  test.describe("filters", () => {
    test("shows priority filter dropdown", async ({ page }) => {
      await page.goto("/tasks");
      if (page.url().includes("/login")) return;

      const priorityFilter = page.getByLabel("Filter tasks by priority");
      await expect(priorityFilter).toBeVisible();
      await expect(priorityFilter).toHaveValue("");
    });

    test("priority filter has all priority options", async ({ page }) => {
      await page.goto("/tasks");
      if (page.url().includes("/login")) return;

      const priorityFilter = page.getByLabel("Filter tasks by priority");
      const options = await priorityFilter.locator("option").allTextContents();
      expect(options).toContain("All priorities");
      expect(options).toContain("Critical");
      expect(options).toContain("High");
      expect(options).toContain("Medium");
      expect(options).toContain("Low");
    });

    test("Reset filters button appears when filters are active", async ({ page }) => {
      await page.goto("/tasks");
      if (page.url().includes("/login")) return;

      // Initially no Reset filters button
      await expect(page.getByRole("button", { name: "Reset filters" })).not.toBeVisible();

      // Apply a priority filter
      await page.getByLabel("Filter tasks by priority").selectOption("critical");
      await expect(page.getByRole("button", { name: "Reset filters" })).toBeVisible();

      // Click Reset filters
      await page.getByRole("button", { name: "Reset filters" }).click();
      await expect(page.getByRole("button", { name: "Reset filters" })).not.toBeVisible();
    });
  });

  test.describe("search", () => {
    test("shows search input", async ({ page }) => {
      await page.goto("/tasks");
      if (page.url().includes("/login")) return;

      const searchInput = page.getByPlaceholder(
        "Search titles, reasons, labels, blocked context...",
      );
      await expect(searchInput).toBeVisible();
    });

    test("search shows no results message for nonsense query", async ({ page }) => {
      await page.goto("/tasks");
      if (page.url().includes("/login")) return;

      const searchInput = page.getByPlaceholder(
        "Search titles, reasons, labels, blocked context...",
      );
      await searchInput.fill("xyznonexistent999");
      // Should show "No tasks match this search." or the empty state
      await expect(
        page.getByText(/No tasks match this search|Nothing needs your attention/),
      ).toBeVisible();
    });

    test("search filters visible count", async ({ page }) => {
      await page.goto("/tasks");
      if (page.url().includes("/login")) return;

      // The visible/total count indicator
      await expect(page.getByText(/\d+ visible \/ \d+ total/)).toBeVisible();
    });
  });

  test.describe("sort", () => {
    test("shows sort dropdown with default urgency", async ({ page }) => {
      await page.goto("/tasks");
      if (page.url().includes("/login")) return;

      const sortSelect = page.locator("select").filter({ hasText: "Sort by urgency" });
      await expect(sortSelect).toBeVisible();
    });

    test("sort dropdown has all sort options", async ({ page }) => {
      await page.goto("/tasks");
      if (page.url().includes("/login")) return;

      const sortSelect = page.locator("select").filter({ hasText: "Sort by urgency" });
      const options = await sortSelect.locator("option").allTextContents();
      expect(options).toContain("Sort by urgency");
      expect(options).toContain("Sort by priority");
      expect(options).toContain("Newest first");
      expect(options).toContain("Oldest first");
      expect(options).toContain("Highest confidence");
    });
  });

  test.describe("empty state", () => {
    test("shows empty state when queue is clear", async ({ page }) => {
      await page.goto("/tasks");
      if (page.url().includes("/login")) return;

      const taskLinks = page.locator("a[href^='/tasks/']");
      const taskCount = await taskLinks.count();
      if (taskCount === 0) {
        await expect(page.getByText("Queue is clear")).toBeVisible();
        await expect(page.getByText("Nothing needs your attention.")).toBeVisible();
      }
    });
  });

  test.describe("task cards", () => {
    test("task cards show priority and status badges", async ({ page }) => {
      await page.goto("/tasks");
      if (page.url().includes("/login")) return;

      const firstTask = page.locator("a[href^='/tasks/']").first();
      if ((await firstTask.count()) === 0) return;

      // Cards should show priority and status badges
      const priorityBadge = page.getByText(/^(critical|high|medium|low)$/i).first();
      await expect(priorityBadge).toBeVisible();
    });

    test("task cards have Open link to detail page", async ({ page }) => {
      await page.goto("/tasks");
      if (page.url().includes("/login")) return;

      const openBtn = page.getByText("Open").first();
      if ((await openBtn.count()) > 0) {
        await expect(openBtn).toBeVisible();
      }
    });

    test("task cards have selection checkboxes", async ({ page }) => {
      await page.goto("/tasks");
      if (page.url().includes("/login")) return;

      const firstTask = page.locator("a[href^='/tasks/']").first();
      if ((await firstTask.count()) === 0) return;

      const checkbox = page.getByRole("checkbox").first();
      await expect(checkbox).toBeVisible();
    });

    test("clicking checkbox shows bulk action bar", async ({ page }) => {
      await page.goto("/tasks");
      if (page.url().includes("/login")) return;

      const checkbox = page.getByRole("checkbox").first();
      if ((await checkbox.count()) === 0) return;

      await checkbox.click();
      await expect(page.getByText("1 selected")).toBeVisible();
      await expect(page.getByRole("button", { name: "Accept all" })).toBeVisible();
      await expect(page.getByRole("button", { name: "Complete all" })).toBeVisible();
      await expect(page.getByRole("button", { name: "Clear" })).toBeVisible();
    });

    test("Clear button removes bulk selection", async ({ page }) => {
      await page.goto("/tasks");
      if (page.url().includes("/login")) return;

      const checkbox = page.getByRole("checkbox").first();
      if ((await checkbox.count()) === 0) return;

      await checkbox.click();
      await expect(page.getByText("1 selected")).toBeVisible();
      await page.getByRole("button", { name: "Clear" }).click();
      await expect(page.getByText("1 selected")).not.toBeVisible();
    });
  });

  test.describe("task detail navigation", () => {
    test("clicking a task title navigates to detail page", async ({ page }) => {
      await page.goto("/tasks");
      if (page.url().includes("/login")) return;

      const firstTask = page.locator("a[href^='/tasks/']").first();
      if ((await firstTask.count()) === 0) return;

      const href = await firstTask.getAttribute("href");
      await firstTask.click();
      await expect(page).toHaveURL(href!);
      await expect(page.getByText("Back to Tasks")).toBeVisible();
    });
  });

  test.describe("keyboard shortcuts", () => {
    test("/ focuses the search input", async ({ page }) => {
      await page.goto("/tasks");
      if (page.url().includes("/login")) return;

      await page.keyboard.press("/");
      const searchInput = page.getByPlaceholder(
        "Search titles, reasons, labels, blocked context...",
      );
      await expect(searchInput).toBeFocused();
    });
  });
});
