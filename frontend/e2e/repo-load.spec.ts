import { test, expect } from "@playwright/test";

const ALF_LOGIC_PATH = "/Users/alexfetisov/dev/showcase-example";

test.describe("Repository Loading", () => {
  test("loads alf-logic repo and displays all 10 functions", async ({ page }) => {
    await page.goto("/");

    // Verify the page loaded
    await expect(page.locator("h1")).toHaveText("Formal Verification Pipeline");

    // Enter repo path
    const input = page.getByTestId("repo-input");
    await input.fill(ALF_LOGIC_PATH);

    // Click load
    const loadBtn = page.getByTestId("load-button");
    await loadBtn.click();

    // Wait for the file tree to appear
    const fileTree = page.getByTestId("file-tree");
    await expect(fileTree).toBeVisible({ timeout: 15000 });

    // Verify repo name is shown
    await expect(fileTree).toContainText("showcase-example");

    // Verify function count
    await expect(fileTree).toContainText("10 functions found");

    // Expand the chunker directory and verify functions
    await page.getByText("chunker").first().click();
    await expect(page.getByText("split_file")).toBeVisible();
    await expect(page.getByText("calculate_boundaries")).toBeVisible();
    await expect(page.getByText("merge_chunks")).toBeVisible();
    await expect(page.getByText("validate_checksum")).toBeVisible();
    await expect(page.getByText("handle_partial_chunk")).toBeVisible();

    // Expand the hashmap directory and verify functions
    await page.getByText("hashmap").first().click();
    await expect(page.getByText("hash_key")).toBeVisible();
    await expect(page.getByText("put")).toBeVisible();
    await expect(page.getByText("get")).toBeVisible();
    await expect(page.getByText("resize")).toBeVisible();
    await expect(page.getByText("delete")).toBeVisible();
  });

  test("shows error for invalid repo path", async ({ page }) => {
    await page.goto("/");

    const input = page.getByTestId("repo-input");
    await input.fill("/nonexistent/repo/path");

    await page.getByTestId("load-button").click();

    const error = page.getByTestId("error-message");
    await expect(error).toBeVisible({ timeout: 10000 });
    await expect(error).toContainText("Failed to clone");
  });
});
