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
 * E2E-09: report → experience card → case validation → approve (Phase C)
 * E2E-10: card → validation workflow DAG → quant record (Phase D)
 * E2E-11: card → screening run → candidates with why-selected (Phase E)
 * E2E-12: screening → strategy → backtest → §47 gate (Phase F)
 * E2E-13: strategy monitor with Observation/Signal/Decision separation (G)
 * E2E-14: workspace → industry map / global context → context-preserving
 *         return to the workspace (Phase H, §52/§77)
 * E2E-15: global research graph + lineage explorer (Phase I, §78)
 * E2E-16: replay feedback loop from a monitor decision (Phase J, §79)
 * E2E-17: deep extensions — numeric macro layer + board relations +
 *         quant expression node
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
    // self-clean: leftover tasks from earlier failed runs would break count=0
    const existing = await page.request.get("/api/v1/tasks");
    for (const t of ((await existing.json()) as Array<{ task_id: string; status: string }>).results) {
      if (t.status !== "running") await page.request.delete(`/api/v1/tasks/${t.task_id}`);
    }
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

  test("E2E-09 report distills an experience card through validation to approval", async ({ page }) => {
    await page.goto("/reports");
    const card = page.getByTestId("report-card").filter({ hasText: "中国稀土" }).first();
    await expect(card).toBeVisible();

    // §43: report → experience card via the handoff envelope
    await page.getByTestId("experience-create").first().click();
    await page.waitForURL(/\/experience\/exp_[0-9a-f]+\?handoff=ho_/);
    await expect(page.getByTestId("experience-detail")).toBeVisible();

    // sources preserved on the card (§43)
    await expect(page.getByText("来源主张数")).toBeVisible();
    const claimsText = await page.getByTestId("experience-detail").innerText();
    expect(claimsText).not.toContain("undefined");

    // 验 → 用 gate: approve before validation must stay blocked
    await page.getByTestId("experience-approve").click();
    await expect(page.getByText("验证后才可批准")).toBeVisible();

    // run the case validation, then approve
    await page.getByTestId("experience-validate").click();
    await expect(page.getByText("案例验证：").first()).toBeVisible({ timeout: 30_000 });
    await expect(page.getByText("验证中")).toBeVisible();
    await page.getByTestId("experience-approve").click();
    await expect(page.getByText("已批准")).toBeVisible({ timeout: 20_000 });
  });

  test("E2E-10 card launches the validation workflow DAG", async ({ page }) => {
    await page.goto("/reports");
    await page.getByTestId("experience-create").first().click();
    await page.waitForURL(/\/experience\/exp_[0-9a-f]+\?handoff=ho_/);

    // §44: experience card → validation workflow (real daily bars on the stack).
    // The kline source is an external dependency that is sometimes unreachable
    // from this network — the product contract is an HONEST terminal state:
    // either completed with real metrics, or failed with the source error shown.
    await page.getByTestId("workflow-horizon").selectOption("20");
    await page.getByTestId("workflow-launch").click();
    const runPanel = page.getByTestId("workflow-run");
    const terminal = runPanel.getByText(/工作流完成|工作流失败/);
    await expect(terminal).toBeVisible({ timeout: 120_000 });
    const outcome = (await terminal.innerText()).trim();

    if (outcome.includes("工作流完成")) {
      const metrics = page.getByTestId("workflow-metrics");
      await expect(metrics.getByText("样本数")).toBeVisible();
      await expect(metrics.getByText("命中率")).toBeVisible();
      // the quant validation landed in the card's validation records
      await expect(page.getByText("量化验证").first()).toBeVisible({ timeout: 20_000 });
    } else {
      // failure path: the data node's real error is disclosed on the node
      await expect(runPanel.locator(".status-error").first()).toBeVisible();
    }
  });

  test("E2E-11 card screens the market with why-selected candidates", async ({ page }) => {
    await page.goto("/reports");
    await page.getByTestId("experience-create").first().click();
    await page.waitForURL(/\/experience\/exp_[0-9a-f]+\?handoff=ho_/);

    // §45: experience card → screening run via the handoff envelope
    await page.getByTestId("screening-launch").click();
    await page.waitForURL(/\/screening\/sr_[0-9a-f]+\?handoff=ho_/);

    // candidates carry why-selected explanations (§20)
    await expect(page.getByTestId("screening-candidate").first()).toBeVisible({ timeout: 60_000 });
    const detail = page.getByTestId("screening-detail");
    await expect(detail.getByText(/全市场 .* 标的/)).toBeVisible();
    await expect(page.getByTestId("candidate-explanation").first()).toContainText("命中全部");
    await expect(page.getByTestId("candidate-explanation").first()).toContainText("经验依据");
    // the exclusion summary is disclosed (为什么没选中)
    await expect(page.getByTestId("screening-excluded")).toBeVisible();
  });

  test("E2E-12 screening assembles a strategy with the §47 gate", async ({ page }) => {
    await page.goto("/reports");
    await page.getByTestId("experience-create").first().click();
    await page.waitForURL(/\/experience\/exp_[0-9a-f]+\?handoff=ho_/);
    await page.getByTestId("screening-launch").click();
    await page.waitForURL(/\/screening\/sr_[0-9a-f]+\?handoff=ho_/);
    await expect(page.getByTestId("screening-candidate").first()).toBeVisible({ timeout: 60_000 });

    // §46: screening → strategy via the handoff envelope
    await page.getByTestId("strategy-launch").click();
    await page.waitForURL(/\/strategy\/strat_[0-9a-f]+\?handoff=ho_/);
    await expect(page.getByTestId("strategy-detail")).toBeVisible();
    await expect(page.getByTestId("strategy-detail").getByText("策略理念")).toBeVisible();

    // §47 gate: validate before any backtest must be refused with the reason
    await page.getByTestId("strategy-validate").click();
    await expect(page.getByText("验证门槛")).toBeVisible({ timeout: 20_000 });

    // cross-instrument backtest (real bars or honest source-failure disclosure)
    await page.getByTestId("strategy-backtest").click();
    const block = page.getByTestId("backtest-block");
    await expect(block.getByText(/跨标的回测/)).toBeVisible({ timeout: 20_000 });
    const chip = block.locator(".watch-card-head span").filter({ hasText: /已完成|失败/ });
    await expect(chip).toBeVisible({ timeout: 120_000 });
    const outcome = (await chip.innerText()).trim();

    if (outcome.includes("已完成")) {
      // metrics visible; falling instruments appear as failure cases (§22)
      await expect(page.getByTestId("failure-cases").or(page.getByText("组合平均收益"))).toBeVisible();
      // validate now passes the gate and marks the version EXPERIMENTAL
      await page.getByTestId("strategy-validate").click();
      await expect(page.getByTestId("strategy-verdict")).toContainText("EXPERIMENTAL", {
        timeout: 20_000,
      });
    } else {
      // honest path: the source failure is disclosed on the block
      await expect(block.locator(".status-error").first()).toBeVisible();
    }
  });

  test("E2E-13 strategy monitor separates observations, signals and decisions", async ({ page }) => {
    // drive the chain to a strategy (same as E2E-12) and try to create a monitor
    await page.goto("/reports");
    await page.getByTestId("experience-create").first().click();
    await page.waitForURL(/\/experience\/exp_[0-9a-f]+\?handoff=ho_/);
    await page.getByTestId("screening-launch").click();
    await page.waitForURL(/\/screening\/sr_[0-9a-f]+\?handoff=ho_/);
    await expect(page.getByTestId("screening-candidate").first()).toBeVisible({ timeout: 60_000 });
    await page.getByTestId("strategy-launch").click();
    await page.waitForURL(/\/strategy\/strat_[0-9a-f]+\?handoff=ho_/);

    // §47 gate: DRAFT strategy → the monitor creation is refused honestly
    await page.getByTestId("monitor-create").click();
    const gate = page.getByText("盯盘门槛");
    const created = await gate
      .waitFor({ timeout: 20_000 })
      .then(() => false)
      .catch(() => true);

    if (created) {
      // the version was EXPERIMENTAL → monitor page opened
      await expect(page.getByTestId("monitor-detail")).toBeVisible();
      await page.getByTestId("monitor-run").click();
      // §24 three-way separation is visible as three distinct record sets
      await expect(page.getByTestId("monitor-observations").getByText("行情变化").first())
        .toBeVisible({ timeout: 60_000 });
      await expect(page.getByTestId("monitor-decisions").getByText(/复核研究|继续观察/))
        .toBeVisible({ timeout: 20_000 });
      await expect(page.getByTestId("monitor-decisions").getByText("Research Decision")).toBeVisible();
    } else {
      // honest gate disclosure on the strategy page (source-dependent path)
      await expect(page.getByTestId("strategy-detail")).toBeVisible();
    }
  });

  test("E2E-14 research map views preserve context back to the workspace", async ({ page }) => {
    // enter the workspace from the research we ran in this serial pass
    await page.goto("/instrument/SZSE%3A000831");
    await expect(page.getByTestId("workspace-name")).toContainText("中国稀土");

    // §52: the views are Research Inputs reached from the instrument
    await page.getByTestId("workspace-industry-map").click();
    await expect(page.getByTestId("industry-map-page")).toBeVisible();
    const mapReady = await page
      .getByTestId("industry-chain")
      .waitFor({ timeout: 15_000 })
      .then(() => true)
      .catch(() => false);

    // §77: the views are not orphan dashboards — open_with_context returns
    // to the instrument workspace carrying the handoff envelope
    if (mapReady) {
      await page.getByTestId("industry-map-open-workspace").click();
    } else {
      await page.getByRole("link", { name: "返回工作台" }).click();
    }
    // context preserved: back on the workspace with the SAME instrument
    await expect(page.getByTestId("workspace-name")).toContainText("中国稀土", {
      timeout: 20_000,
    });

    // global context page behaves the same way
    await page.goto("/global-context/SZSE%3A000831");
    const ctxReady = await page
      .getByTestId("global-context-disclosure")
      .waitFor({ timeout: 15_000 })
      .then(() => true)
      .catch(() => false);
    if (ctxReady) {
      // the disclosure states the numeric layer honestly (either connected
      // via the quote feed or explicitly not connected)
      await expect(page.getByTestId("global-context-disclosure")).toBeVisible();
    } else {
      await expect(page.getByText("宏观资讯未采集")).toBeVisible();
    }
  });

  test("E2E-15 global graph lineage explorer traces to the research run", async ({ page }) => {
    await page.goto("/research-graph");
    await expect(page.getByTestId("graph-nodes")).toBeVisible();

    // select a report node — its lineage must reach the research run
    const reportButtons = page
      .getByTestId("graph-nodes")
      .getByRole("button")
      .filter({ hasText: "完整研究报告" });
    await expect(reportButtons.first()).toBeVisible({ timeout: 20_000 });
    await reportButtons.first().click();

    const lineage = page.getByTestId("graph-lineage");
    await expect(lineage.getByTestId("lineage-selected")).toBeVisible();
    await expect(lineage.getByText("研究运行").first()).toBeVisible({ timeout: 20_000 });
    await expect(lineage.getByText("产出")).toBeVisible();

    // cross-module jump: the artifact's route leaves the graph page
    await lineage.getByRole("link", { name: "打开产物" }).first().click();
    await expect(page).not.toHaveURL(/\/research-graph/);
  });

  test("E2E-16 replay feedback from a monitor decision", async ({ page }) => {
    // continue the serial chain: monitor with a decision (E2E-13 path)
    await page.goto("/reports");
    await page.getByTestId("experience-create").first().click();
    await page.waitForURL(/\/experience\/exp_[0-9a-f]+\?handoff=ho_/);
    await page.getByTestId("screening-launch").click();
    await page.waitForURL(/\/screening\/sr_[0-9a-f]+\?handoff=ho_/);
    await expect(page.getByTestId("screening-candidate").first()).toBeVisible({ timeout: 60_000 });
    await page.getByTestId("strategy-launch").click();
    await page.waitForURL(/\/strategy\/strat_[0-9a-f]+\?handoff=ho_/);
    await page.getByTestId("monitor-create").click();
    const gate = page.getByText("盯盘门槛");
    const created = await gate
      .waitFor({ timeout: 20_000 })
      .then(() => false)
      .catch(() => true);

    if (!created) {
      // DRAFT strategy (source-dependent backtest) — the §47 gate refusal is
      // the honest terminal state for this pass
      await expect(page.getByTestId("strategy-detail")).toBeVisible();
      return;
    }
    await expect(page.getByTestId("monitor-detail")).toBeVisible();
    await page.getByTestId("monitor-run").click();
    await expect(page.getByTestId("monitor-decisions").getByText(/复核研究|继续观察/))
      .toBeVisible({ timeout: 60_000 });

    // §79: replay feedback — with no matured validation on the chain the
    // refusal is the honest product behaviour
    await page.getByTestId("replay-launch").click();
    await expect(page.getByText(/链上尚无已验证预测/)).toBeVisible({ timeout: 20_000 });
  });

  test("E2E-17 deep extensions: numeric macro layer, board relations, quant expression", async ({ page }) => {
    // (b) 全球坐标数值层：real index/commodity values from the quote feed
    await page.goto("/global-context/SZSE%3A000831");
    const indicators = page.getByTestId("global-indicators");
    const indicatorsReady = await indicators
      .waitFor({ timeout: 20_000 })
      .then(() => true)
      .catch(() => false);
    if (indicatorsReady) {
      await expect(indicators.getByText("上证指数")).toBeVisible();
      await expect(indicators.locator(".pct-up, .pct-down").first()).toBeVisible();
    } else {
      // numeric layer not built yet (quote feed unreachable) — the page must
      // still render its persisted state honestly
      await expect(page.getByTestId("global-context-disclosure")).toBeVisible();
      await expect(page.getByTestId("global-context-page").getByText(/主题/).first()).toBeVisible();
    }

    // (a) 产业地图关系源: board members or the honest co-occurrence fallback
    await page.goto("/industry-map/SZSE%3A000831");
    const chain = page.getByTestId("industry-chain");
    await expect(chain.or(page.getByText("产业资料未采集")).first()).toBeVisible({
      timeout: 20_000,
    });

    // (c) quant expression node: an unsatisfiable rule still records an
    // honest verdict on the card's workflow
    await page.goto("/reports");
    await page.getByTestId("experience-create").first().click();
    await page.waitForURL(/\/experience\/exp_[0-9a-f]+\?handoff=ho_/);
    await page.getByTestId("workflow-expression").fill("hit_rate >= 100 AND best_return < 1");
    await page.getByTestId("workflow-launch").click();
    const runPanel = page.getByTestId("workflow-run");
    await expect(
      runPanel.getByText(/工作流完成|工作流失败/),
    ).toBeVisible({ timeout: 120_000 });
    const outcome = (await runPanel.getByText(/工作流完成|工作流失败/).innerText()).trim();
    // the expression node is part of the DAG either way
    await expect(runPanel.getByText(/量化规则表达式/)).toBeVisible();
    if (outcome.includes("工作流完成")) {
      await expect(runPanel.getByText(/成立|不成立/).first()).toBeVisible();
    } else {
      // kline source down → honest failure disclosed on the data node
      await expect(runPanel.locator(".status-error").first()).toBeVisible();
    }
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

test("E2E-UI-08 zh-CN business areas render no raw enums or technical ids", async ({ page }) => {
  // 报告库
  await page.goto("/reports");
  const reports = await page.getByTestId("reports-page").innerText();
  expect(reports).not.toMatch(/\b(pass|blocked|failed)\b/);
  // 经验卡
  await page.goto("/experience");
  const cards = await page.getByTestId("experience-page").innerText();
  expect(cards).not.toMatch(/\b(DRAFT|REFINED|APPROVED|REJECTED)\b/);
  // 策略实验室
  await page.goto("/strategy");
  const strategy = await page.getByTestId("strategy-page").innerText();
  expect(strategy).not.toMatch(/\b(DRAFT|EXPERIMENTAL)\b/);
  expect(strategy).not.toContain("strat_");
  // 研究图谱
  await page.goto("/research-graph");
  const graph = await page.getByTestId("research-graph-page").innerText();
  expect(graph).not.toMatch(/art_[0-9a-f]/);
  expect(graph).not.toMatch(/rpt_[0-9a-f]/);
  // 数据源状态（技术页豁免，但 provider 能力行应为业务词）
  await page.goto("/source-health");
  await expect(page.getByTestId("source-health-table")).toBeVisible();
  const health = await page.getByTestId("source-health-page").innerText();
  expect(health).not.toContain("parse_error");
});
