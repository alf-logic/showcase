import { test, expect } from "@playwright/test";

const REPO_PATH = "/Users/alexfetisov/dev/showcase-example";

test.describe("Agents & Git Tab", () => {
  test("shows agent conversations and git graph after pipeline completes", async ({ page }) => {
    test.setTimeout(360000);

    // Load repo and run pipeline
    await page.goto("/");
    await page.getByTestId("repo-input").fill(REPO_PATH);
    await page.getByTestId("load-button").click();
    await expect(page.getByTestId("file-tree")).toBeVisible({ timeout: 15000 });
    await page.getByTestId("generate-button").click();
    await expect(page.getByTestId("pipeline-complete")).toBeVisible({ timeout: 360000 });

    // Switch to Agents & Git tab
    await page.getByTestId("bottom-tab-agents").click();

    // Wait for agent data to load
    await expect(page.locator("text=Spec Agent")).toBeVisible({ timeout: 10000 });
    await expect(page.locator("text=Reviewer")).toBeVisible();

    // Verify git graph rendered
    await expect(page.getByTestId("git-graph")).toBeVisible();
    const svgElements = page.locator("[data-testid='git-graph'] svg circle");
    const circleCount = await svgElements.count();
    expect(circleCount).toBeGreaterThan(5); // At least several commits

    // Verify agent panel has content for at least one function
    const agentContent = page.locator("text=/gpt-4o/i").first();
    await expect(agentContent).toBeVisible({ timeout: 5000 });

    console.log(`Git graph has ${circleCount} commit nodes`);
  });
});
