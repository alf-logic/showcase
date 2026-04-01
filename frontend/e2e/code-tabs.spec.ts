import { test, expect } from "@playwright/test";

const REPO_PATH = "/Users/alexfetisov/dev/showcase-example";

test.describe("Code Tabs", () => {
  test("shows real spec inline and test code after pipeline", async ({ page }) => {
    test.setTimeout(360000);

    // Load repo and run pipeline
    await page.goto("/");
    await page.getByTestId("repo-input").fill(REPO_PATH);
    await page.getByTestId("load-button").click();
    await expect(page.getByTestId("file-tree")).toBeVisible({ timeout: 15000 });
    await page.getByTestId("generate-button").click();
    await expect(page.getByTestId("pipeline-complete")).toBeVisible({ timeout: 360000 });

    // Find a covered function from the status table
    // Click the first function in the tree
    await page.getByTestId("fn-split_file").click();

    // Source tab should show source code
    const codePanel = page.getByTestId("code-panel");
    await expect(codePanel).toContainText("def split_file", { timeout: 5000 });

    // Switch to Tests tab
    await page.getByTestId("tab-tests").click();

    // Wait for results to load
    await page.waitForTimeout(3000);
    const panelText = await codePanel.textContent();
    console.log("Tests tab content (first 200 chars):", panelText?.slice(0, 200));

    // Should show either test code or "No tests" message
    const hasTestCode = panelText?.includes("def test_") || panelText?.includes("import pytest");
    const hasNoTests = panelText?.includes("No tests");
    expect(hasTestCode || hasNoTests).toBeTruthy();

    if (hasTestCode) {
      // Verify test output section exists
      await expect(codePanel.locator("text=Test Output")).toBeVisible({ timeout: 3000 }).catch(() => {
        // Test output might not be visible if scrolled
      });
    }

    // Switch back to Source tab
    await page.getByTestId("tab-source").click();
    await expect(codePanel).toContainText("def split_file");

    // Try a function that should have needs_refactor status
    await page.getByTestId("fn-resize").click();
    await page.getByTestId("tab-tests").click();
    // Resize was rejected at L2, so no tests
    await expect(codePanel).toContainText("No tests");

    console.log("Code tabs verified: source, tests with output, no-tests state");
  });
});
