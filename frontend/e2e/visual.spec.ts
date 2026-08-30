import { expect, test } from "@playwright/test";

/**
 * UI8 — Visual Regression（任务书 §49）：
 * 核心页面截图基线（zh-CN Light 全量 + Dark 抽样）。
 * 基线首次生成：npx playwright test --update-snapshots visual.spec.ts
 */

const PAGES: Array<{ name: string; path: string; wait: string }> = [
  { name: "command-center", path: "/", wait: "[data-testid=commander-page]" },
  { name: "watchlist", path: "/watchlist", wait: "[data-testid=watchlist-page]" },
  { name: "reports", path: "/reports", wait: "[data-testid=reports-page]" },
  { name: "predictions", path: "/predictions", wait: "[data-testid=predictions-page]" },
  { name: "experience", path: "/experience", wait: "[data-testid=experience-page]" },
  { name: "workflows", path: "/workflows", wait: "[data-testid=workflows-page]" },
  { name: "screening", path: "/screening", wait: "[data-testid=screening-page]" },
  { name: "strategy", path: "/strategy", wait: "[data-testid=strategy-page]" },
  { name: "monitoring", path: "/monitoring", wait: "[data-testid=monitors-page]" },
  { name: "source-health", path: "/source-health", wait: "[data-testid=source-health-page]" },
];

test.describe("visual regression zh-CN light", () => {
  for (const p of PAGES) {
    test(`screenshot ${p.name} (zh light)`, async ({ page }) => {
      await page.goto(p.path);
      await page.locator(p.wait).waitFor({ timeout: 20_000 });
      await page.waitForTimeout(600);
      await expect(page).toHaveScreenshot(`${p.name}-zh-light.png`, {
        fullPage: true,
        animations: "disabled",
        maxDiffPixelRatio: 0.35,
        mask: [page.locator(".watch-card-quote"), page.locator(".mono")],
      });
    });
  }
});

test.describe("visual regression dark", () => {
  test.use({ colorScheme: "dark" });
  test("screenshot watchlist (zh dark)", async ({ page }) => {
    await page.goto("/watchlist");
    await page.evaluate(() => document.documentElement.setAttribute("data-theme", "dark"));
    await page.waitForTimeout(600);
    await expect(page).toHaveScreenshot("watchlist-zh-dark.png", {
      fullPage: true,
      animations: "disabled",
      maxDiffPixelRatio: 0.35,
      mask: [page.locator(".watch-card-quote"), page.locator(".mono")],
    });
  });
  test("screenshot command-center (zh dark)", async ({ page }) => {
    await page.goto("/");
    await page.evaluate(() => document.documentElement.setAttribute("data-theme", "dark"));
    await page.locator("[data-testid=commander-page]").waitFor({ timeout: 20_000 });
    await page.waitForTimeout(600);
    await expect(page).toHaveScreenshot("command-center-zh-dark.png", {
      fullPage: true,
      animations: "disabled",
      maxDiffPixelRatio: 0.35,
      mask: [page.locator(".watch-card-quote"), page.locator(".mono")],
    });
  });
});
