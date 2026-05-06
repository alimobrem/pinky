import { test as setup } from "@playwright/test";

/**
 * Global setup: create an authenticated session for E2E tests.
 *
 * Sets a test session cookie by calling the API directly.
 * The API must be running with PINKY_TEST_AUTH=true which enables
 * a test login endpoint that bypasses OAuth.
 *
 * If the test login endpoint isn't available, tests will still run
 * but skip auth-required pages (existing behavior).
 */
setup("authenticate", async ({ page }) => {
  try {
    // Try the test login endpoint (available when PINKY_TEST_AUTH=true)
    const response = await page.request.post("http://localhost:8000/api/v1/auth/test-login", {
      data: { username: "test-admin", groups: ["pinky-admins"] },
    });

    if (response.ok()) {
      // The response sets session cookies — save browser state
      await page.context().storageState({ path: "tests/e2e/.auth-state.json" });
      return;
    }
  } catch {
    // Test login not available — try regular session check
  }

  // Fallback: check if there's already a valid session (e.g., from manual login)
  await page.goto("http://localhost:3000/dashboard");
  if (!page.url().includes("/login")) {
    await page.context().storageState({ path: "tests/e2e/.auth-state.json" });
  }
});
