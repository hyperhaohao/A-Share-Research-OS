import { beforeEach, describe, expect, it } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import i18n from "../src/i18n";
import { MonitorReplay, type ReplayRecord } from "../src/features/strategy-monitor/MonitorReplay";
import { MonitorCandles } from "../src/features/strategy-monitor/MonitorCandles";

const records: ReplayRecord[] = [
  { id: "o1", kind: "observation", at: "2026-08-30T01:00:00Z", text: "价格变化 60.18" },
  { id: "s1", kind: "signal", at: "2026-08-30T01:00:00Z", text: "quote_move 强度 0.8" },
  { id: "d1", kind: "decision", at: "2026-08-30T01:05:00Z", text: "继续观察 · 无成熟信号" },
];

describe("Strategy Monitor — Replay（方案 §18）", () => {
  beforeEach(async () => {
    await i18n.changeLanguage("zh-CN");
  });

  it("sorts records chronologically and scrubs the timeline", () => {
    render(<MonitorReplay records={[...records].reverse()} />);
    const slider = screen.getByRole("slider") as HTMLInputElement;
    expect(slider.max).toBe("3");
    // default = full replay
    expect(screen.getByText("价格变化 60.18")).toBeTruthy();
    expect(screen.getByText("继续观察 · 无成熟信号")).toBeTruthy();
    // scrub to 0 → nothing shown yet
    fireEvent.change(slider, { target: { value: "0" } });
    expect(screen.getByText("拖动滑块推进时间线")).toBeTruthy();
    // scrub to 2 → obs+signal visible, decision not yet
    fireEvent.change(slider, { target: { value: "2" } });
    expect(screen.getByText("价格变化 60.18")).toBeTruthy();
    expect(screen.queryByText("继续观察 · 无成熟信号")).toBeNull();
  });

  it("renders honest empty state without records", () => {
    render(<MonitorReplay records={[]} />);
    expect(screen.getByText("暂无记录可回放")).toBeTruthy();
  });
});

describe("Strategy Monitor — K线区（G0 Candles 复用）", () => {
  beforeEach(async () => {
    await i18n.changeLanguage("zh-CN");
  });

  it("renders honest empty state without bars (never fakes a chart)", () => {
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <QueryClientProvider client={client}>
        <MonitorCandles instrumentId="SZSE:000831" signals={[]} />
      </QueryClientProvider>,
    );
    // fetch fails in jsdom → error state; either way no <svg> candles appear
    const svg = document.querySelector("[data-testid=monitor-candles] svg");
    expect(svg).toBeNull();
  });
});
