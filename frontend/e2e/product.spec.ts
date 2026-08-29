import { expect, test } from "@playwright/test";

/**
 * 产品闭环 E2E（整改方案 §20，核心回归标的 000831 中国稀土）。
 * E2E-01/02: identity + watchlist + workspace
 * E2E-03: SSE live research stages
 * E2E-04: task create → run → delete → history preserved
 * E2E-05: report → prediction via handoff envelope (V2 Phase A)
 * E2E-06: single-select appearance/language + no raw enums in zh-CN
 * E2E-07: report lineage backtracks to its research run (V2 Phase A)
 * E2E-08: conversation → plan → research run → report (V2 Phase B 中枢)
 */

test.describe.serial("000831 product flow", () => {
  test("E2E-01 search 000831 shows business identity without raw codes", async ({ page }) => {
    await page.goto("/");
    await page.getByTestId("instrument-search").getByRole("textbox").fill("000831");
    await page.getByTestId("instrument-search").getByRole("button").click();

    const results = page.getByTestId("search-results");
    await expect(results.getByText("中国稀土")).toBeVisible();
    await expect(results.getByText(/深交所/)).toBeVisible();
    const text = await results.innerText();
    expect(text).not.toContain("SZSE");
    expect(text).not.toContain("main_board");
  });

  test("E2E-02 watchlist direct add opens workspace", async ({ page }) => {
    await page.goto("/watchlist");
    const form = page.locator("form.search-form");
    await form.getByRole("textbox").fill("000831");
    await form.getByRole("button", { name: "添加关注" }).click();

    await page.getByTestId("watch-card").first().waitFor();
    const card = page.getByTestId("watch-card").first();
    await expect(card.getByText("中国稀土")).toBeVisible();
    await expect(card.getByText(/深交所/)).toBeVisible();

    // workspace opens from the identity line
    await card.getByRole("link", { name: "中国稀土" }).click();
    await expect(page.getByRole("heading", { level: 1 })).toContainText(/中国稀土|000831/);
  });

  test("E2E-03 research run shows live collection and analysis stages", async ({ page }) => {
    await page.goto("/?instrument=SZSE%3A000831&run=1");
    const stages = page.getByTestId("pipeline-stages");
    // live SSE: collection stage lists capabilities one by one (no dedupe)
    await expect(stages.getByText("数据采集")).toBeVisible({ timeout: 30_000 });
    await expect(stages.getByText("实时行情")).toBeVisible();
    // analysis stage lists business analysts
    await expect(stages.getByText("行业分析")).toBeVisible({ timeout: 120_000 });
    await expect(stages.getByText("量化分析")).toBeVisible({ timeout: 120_000 });
    // completion lands the final CTAs
    await expect(page.getByRole("button", { name: "查看报告" })).toBeVisible({ timeout: 180_000 });
    await expect(page.getByRole("button", { name: "打开工作台" })).toBeVisible();
  });

  test("E2E-04 task create, run now, delete keeps history", async ({ page }) => {
    await page.goto("/tasks?instrument=SZSE%3A000831");
    const form = page.locator("form.search-form");
    await form.getByLabel("任务类型").selectOption("prediction_validation");
    await form.getByLabel("频率").selectOption("daily");
    await form.getByLabel("时间").fill("08:30");
    await form.getByRole("button", { name: "创建" }).click();

    const card = page.getByTestId("task-card").first();
    await expect(card.getByText("中国稀土")).toBeVisible();
    await expect(card.getByText("每天 08:30")).toBeVisible();
    await expect(card.getByText("持续研究").or(card.getByText("预测验证"))).toBeVisible();

    // run now → eventually back to 运行正常 (healthy) with a last-run time
    await card.getByRole("button", { name: "立即运行" }).click();
    await expect(card.getByText("运行正常")).toBeVisible({ timeout: 120_000 });

    // delete with the two-step confirm; research history is kept
    await card.getByRole("button", { name: "删除", exact: true }).click();
    await card.getByRole("button", { name: "确认删除" }).click();
    await expect(page.getByTestId("task-card").filter({ hasText: "中国稀土" })).toHaveCount(0);

    // history preserved: watchlist + report library untouched
    await page.goto("/watchlist");
    await expect(page.getByTestId("watch-card").first().getByText("中国稀土")).toBeVisible();
    await page.goto("/reports");
    await expect(page.getByTestId("report-card").first()).toBeVisible();
  });

  test("E2E-05 report creates a prediction shown by business name", async ({ page }) => {
    await page.goto("/reports");
    const card = page.getByTestId("report-card").filter({ hasText: "中国稀土" }).first();
    await expect(card).toBeVisible();

    await card.getByRole("button", { name: "生成预测" }).click();
    await card.getByLabel("预测期限").selectOption("20D");
    await card.getByRole("button", { name: "确认生成" }).click();

    // V2 Phase A: the CTA records a report→prediction handoff envelope and
    // lands on /predictions carrying its handoff + context ids
    await page.waitForURL(/\/predictions\?handoff=ho_[0-9a-f]+&context=ctx_[0-9a-f]+/);
    const predCard = page.getByTestId("prediction-card").filter({ hasText: "中国稀土" }).first();
    await expect(predCard).toBeVisible();
    const text = await predCard.innerText();
    expect(text).not.toContain("SZSE");
  });

  test("E2E-07 report lineage backtracks to the research run", async ({ page }) => {
    await page.goto("/reports");
    const card = page.getByTestId("report-card").filter({ hasText: "中国稀土" }).first();
    await expect(card).toBeVisible();

    await card.getByRole("button", { name: "研究脉络" }).click();
    const lineage = card.getByTestId("report-lineage");
    // upstream: 报告版本 (派生自) ← 研究运行 (产出) — the run is reachable
    await expect(lineage.getByText("报告版本")).toBeVisible({ timeout: 15_000 });
    await expect(lineage.getByText("派生自")).toBeVisible();
    await expect(lineage.getByText("研究运行")).toBeVisible({ timeout: 15_000 });
    await expect(lineage.getByText("产出")).toBeVisible();

    // downstream: the E2E-05 prediction is linked 生成自 this report
    await expect(lineage.getByText("预测")).toBeVisible();
    await expect(lineage.getByText("生成自")).toBeVisible();
  });

  test("E2E-08 conversation plans and completes a research run", async ({ page }) => {
    await page.goto("/");
    // remember the newest plan before the command so we can lock onto OUR plan
    const before = await page.request.get("/api/v1/command/plans?limit=1").then((r) => r.json());
    const previousPlanId: string | null = before.results[0]?.plan_id ?? null;

    await page.getByTestId("commander-input").fill("研究中国稀土最近的资产重组迹象");
    await page.getByTestId("commander-send").click();

    // the commander replies with a structured plan (never a guess)
    await expect(page.getByTestId("commander-reply").last()).toContainText("已创建研究计划", {
      timeout: 20_000,
    });

    // wait for THIS plan (newest id changed) to complete — API is the clock,
    // the UI is the product surface (§42: 对话 → ResearchRun → Artifact → 报告)
    let planId: string | null = null;
    await expect(async () => {
      const body = await page.request.get("/api/v1/command/plans?limit=1").then((r) => r.json());
      const newest = body.results[0];
      expect(newest.plan_id).not.toBe(previousPlanId);
      planId = newest.plan_id;
      expect(newest.status).toBe("completed");
    }).toPass({ timeout: 180_000 });

    // the plan produced a real research run with replayable persisted events
    const planBody = await page.request
      .get(`/api/v1/command/plans/${planId}`)
      .then((r) => r.json());
    expect(planBody.plan.run_id).toBeTruthy();
    const replay = await page.request
      .get(`/api/v1/research-runs/${planBody.plan.run_id}/events`)
      .then((r) => r.json());
    expect(replay.count).toBeGreaterThan(0);

    // right column shows THIS plan's report artifact with a business title
    await expect(page.getByTestId("commander-plan-progress").getByText("计划完成")).toBeVisible({
      timeout: 60_000,
    });
    await expect(
      page.getByTestId("commander-artifacts").getByTestId("artifact-open").first(),
    ).toBeVisible({ timeout: 60_000 });
    const artifactsText = await page.getByTestId("commander-artifacts").innerText();
    expect(artifactsText).toContain("研究报告");
    expect(artifactsText).not.toContain("rpt_");

    // opening the artifact lands on the produced report
    await page.getByTestId("artifact-open").first().click();
    await expect(page).toHaveURL(/\/reports\//);
  });

  test("E2E-06 zh-CN hides raw enums; language select switches to English", async ({ page }) => {
    await page.goto("/watchlist");
    // single-select controls exist
    await expect(page.getByRole("combobox", { name: "外观" })).toBeVisible();
    await expect(page.getByRole("combobox", { name: "界面语言" })).toBeVisible();

    const zhText = await page.getByTestId("watchlist-page").innerText();
    expect(zhText).not.toContain("SZSE");
    expect(zhText).not.toMatch(/\bmonitor\b/);
    expect(zhText).not.toMatch(/\bsucceeded\b/);

    // switch UI language to English through the single select
    await page.getByRole("combobox", { name: "界面语言" }).selectOption("en-US");
    await expect(page.getByRole("heading", { name: "Watchlist" })).toBeVisible();
    await expect(page.getByText("Shenzhen Stock Exchange").first()).toBeVisible();

    // restore zh-CN for the next runs
    await page.getByRole("combobox", { name: "Language" }).selectOption("zh-CN");
    await expect(page.getByRole("heading", { name: "关注列表" })).toBeVisible();
  });
});
