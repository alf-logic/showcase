import { test, expect } from "@playwright/test";

const REPO_PATH = "/Users/alexfetisov/dev/showcase-example";

test.describe("Repository Loading", () => {
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

test.describe("Three-panel layout", () => {
  test("loads repo and shows IDE layout with all 10 functions", async ({ page }) => {
    await page.goto("/");

    // Load the repo
    await page.getByTestId("repo-input").fill(REPO_PATH);
    await page.getByTestId("load-button").click();

    // Verify 3-panel layout appeared
    const fileTree = page.getByTestId("file-tree");
    await expect(fileTree).toBeVisible({ timeout: 15000 });

    // Verify header
    await expect(page.getByText("showcase-example")).toBeVisible();
    await expect(page.getByText("10 functions")).toBeVisible();
    await expect(page.getByTestId("generate-button")).toBeVisible();
    await expect(page.getByTestId("budget-display")).toBeVisible();

    // Verify file tree has all functions
    await expect(page.getByTestId("fn-hash_key")).toBeVisible();
    await expect(page.getByTestId("fn-put")).toBeVisible();
    await expect(page.getByTestId("fn-get")).toBeVisible();
    await expect(page.getByTestId("fn-resize")).toBeVisible();
    await expect(page.getByTestId("fn-delete")).toBeVisible();
    await expect(page.getByTestId("fn-split_file")).toBeVisible();
    await expect(page.getByTestId("fn-calculate_boundaries")).toBeVisible();
    await expect(page.getByTestId("fn-merge_chunks")).toBeVisible();
    await expect(page.getByTestId("fn-validate_checksum")).toBeVisible();
    await expect(page.getByTestId("fn-handle_partial_chunk")).toBeVisible();

    // Verify status table shows all 10 functions as pending
    await expect(page.getByTestId("status-table")).toBeVisible();
    await expect(page.getByTestId("status-row-hash_key")).toBeVisible();
    await expect(page.getByTestId("status-row-split_file")).toBeVisible();

    // Verify tabs exist
    await expect(page.getByTestId("tab-source")).toBeVisible();
    await expect(page.getByTestId("tab-tests")).toBeVisible();
    await expect(page.getByTestId("bottom-tab-status")).toBeVisible();
    await expect(page.getByTestId("bottom-tab-agents")).toBeVisible();
  });

  test("clicking function loads source code", async ({ page }) => {
    await page.goto("/");
    await page.getByTestId("repo-input").fill(REPO_PATH);
    await page.getByTestId("load-button").click();
    await expect(page.getByTestId("file-tree")).toBeVisible({ timeout: 15000 });

    // Click hash_key
    await page.getByTestId("fn-hash_key").click();

    // Verify source code appears
    const codePanel = page.getByTestId("code-panel");
    await expect(codePanel).toContainText("def hash_key");
    await expect(codePanel).toContainText("0x811C9DC5");

    // Click split_file — verify code switches
    await page.getByTestId("fn-split_file").click();
    await expect(codePanel).toContainText("def split_file");
    await expect(codePanel).toContainText("chunk_size");
  });

  test("clicking status table row selects function", async ({ page }) => {
    await page.goto("/");
    await page.getByTestId("repo-input").fill(REPO_PATH);
    await page.getByTestId("load-button").click();
    await expect(page.getByTestId("file-tree")).toBeVisible({ timeout: 15000 });

    // Click resize in status table
    await page.getByTestId("status-row-resize").click();

    // Verify source loaded
    const codePanel = page.getByTestId("code-panel");
    await expect(codePanel).toContainText("def resize");
  });
});
