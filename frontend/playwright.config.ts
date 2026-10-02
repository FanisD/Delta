import { defineConfig, devices } from "@playwright/test"

export default defineConfig({
  testDir: "./e2e",
  timeout: 30_000,
  use: { baseURL: "http://127.0.0.1:8000", trace: "retain-on-failure" },
  webServer: {
    command:
      "cd ../backend && uv run uvicorn app.main:app --host 127.0.0.1 --port 8000",
    url: "http://127.0.0.1:8000/api/health",
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
})
