import { defineConfig } from "@playwright/test";

/**
 * Product E2E (PW3): real browser against the dev stack.
 * Requires the backend on http://127.0.0.1:8000 (compose stack) — the vite
 * dev server proxies /api there. Run: npx playwright test
 */
export default defineConfig({
  testDir: "./e2e",
  timeout: 180_000,
  expect: { timeout: 20_000 },
  fullyParallel: false,
  workers: 1,
  reporter: [["list"]],
  use: {
    baseURL: "http://localhost:5173",
    locale: "zh-CN",
    trace: "retain-on-failure",
  },
  webServer: {
    command: "npm run dev",
    url: "http://localhost:5173",
    reuseExistingServer: true,
    timeout: 60_000,
  },
});
