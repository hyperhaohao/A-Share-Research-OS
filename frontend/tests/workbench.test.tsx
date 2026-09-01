import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import i18n from "../src/i18n";
import {
  resolveTabRoute,
  type WorkbenchTab,
} from "../src/features/command-center/workbench";

function makeTab(overrides: Partial<WorkbenchTab> = {}): WorkbenchTab {
  return {
    tab_id: "tab_abc",
    session_id: "ses_x",
    page: "research-report",
    title: "中国稀土 · 事件调查",
    payload: { report_id: "rpt_1", instrument_ids: ["SZSE:000831"] },
    artifact_id: "art_1",
    is_active: true,
    route: "/reports/{report_id}",
    created_at: null,
    ...overrides,
  };
}

describe("Command Center — Dynamic Workbench (F8, 任务书 §8.7)", () => {
  beforeEach(async () => {
    window.localStorage.clear();
    await i18n.changeLanguage("zh-CN");
  });

  it("resolves payload placeholders and artifact provenance params", () => {
    const route = resolveTabRoute(makeTab());
    expect(route).toBe(
      "/reports/rpt_1?artifact_id=art_1&instrument=SZSE%3A000831",
    );
  });

  it("falls back to plain route when no payload placeholders match", () => {
    const route = resolveTabRoute(
      makeTab({ page: "thesis-center", route: "/thesis", payload: {}, artifact_id: null }),
    );
    expect(route).toBe("/thesis");
  });

  it("renders tabs from server state with active body and full-page CTA", async () => {
    const tabs = [
      makeTab({ tab_id: "tab_a", is_active: false, title: "报告 A", page: "thesis-center", route: "/thesis" }),
      makeTab({ tab_id: "tab_b", is_active: true, title: "报告 B" }),
    ];
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        const url = String(input);
        if (url.includes("/workbench")) {
          return new Response(JSON.stringify({ session_id: "ses_x", tabs }), {
            status: 200,
          });
        }
        return new Response("{}", { status: 200 });
      }),
    );

    const { CommandCenterWorkbench } = await import(
      "../src/features/command-center/CommandCenterWorkbench"
    );
    const client = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    render(
      <QueryClientProvider client={client}>
        <MemoryRouter>
          <CommandCenterWorkbench
            activePlan={null}
            selectedInstrument={null}
            pendingPredictions={[]}
            sessionId="ses_x"
          />
        </MemoryRouter>
      </QueryClientProvider>,
    );

    await waitFor(() => {
      expect(screen.getByTestId("workbench-tabs")).toBeTruthy();
      expect(screen.getByTestId("workbench-tab-research-report")).toBeTruthy();
    });
    // 激活 Tab 的真实数据面（payload 驱动 + 完整页面 CTA）
    expect(screen.getByTestId("workbench-tab-active")).toBeTruthy();
    expect(screen.getAllByText("报告 B").length).toBeGreaterThan(0);
    expect(screen.getByText("在完整页面打开 →")).toBeTruthy();
    vi.unstubAllGlobals();
  });
});
