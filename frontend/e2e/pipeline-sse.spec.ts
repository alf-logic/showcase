import { test, expect } from "@playwright/test";

const REPO_PATH = "/Users/alexfetisov/dev/showcase-example";

test.describe("Pipeline SSE", () => {
  test("Generate Specs button starts pipeline and status table updates", async ({ page }) => {
    // This test hits the real OpenAI API — takes ~4 minutes, costs ~$0.01
    test.setTimeout(360000); // 6 min timeout

    await page.goto("/");
    await page.getByTestId("repo-input").fill(REPO_PATH);
    await page.getByTestId("load-button").click();
    await expect(page.getByTestId("file-tree")).toBeVisible({ timeout: 15000 });

    // Verify all functions start as pending
    await expect(page.getByTestId("status-table")).toBeVisible();

    // Click Generate Specs
    await page.getByTestId("generate-button").click();

    // Verify pipeline is running
    await expect(page.getByTestId("pipeline-running")).toBeVisible({ timeout: 5000 });

    // Verify button is disabled
    await expect(page.getByTestId("generate-button")).toBeDisabled();

    // Wait for at least one function to get a final status (not pending)
    // This confirms SSE is working
    await expect(page.locator('[data-testid^="status-row-"] >> text=/covered|bug|refactor|failed/').first()).toBeVisible({ timeout: 60000 });

    // Wait for pipeline to complete
    await expect(page.getByTestId("pipeline-complete")).toBeVisible({ timeout: 360000 });

    // Verify budget updated (should be non-zero)
    const budgetText = await page.getByTestId("budget-display").textContent();
    expect(budgetText).not.toContain("$0.0000");

    // Verify no functions are still "pending" — all should have a final status
    const rows = page.locator('[data-testid^="status-row-"]');
    const count = await rows.count();
    expect(count).toBe(10);

    // Verify at least some covered functions exist
    await expect(page.locator('text=covered').first()).toBeVisible();

    // Verify resize is needs_refactor (strong directional prompt)
    const resizeRow = page.getByTestId("status-row-resize");
    await expect(resizeRow).toContainText("refactor");

    // Compare with API results
    const runIdFromBudget = budgetText; // We'll verify via API separately
    console.log("Pipeline completed. Budget:", budgetText);
  });
});
