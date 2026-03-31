import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  timeout: 30000,
  use: {
    baseURL: "http://localhost:3000",
    headless: true,
  },
  projects: [
    {
      name: "chromium",
      use: { browserName: "chromium" },
    },
  ],
  webServer: [
    {
      command: "cd ../backend && uv run uvicorn main:app --host 0.0.0.0 --port 8000",
      port: 8000,
      reuseExistingServer: true,
    },
    {
      command: "npm run dev",
      port: 3000,
      reuseExistingServer: true,
    },
  ],
});
