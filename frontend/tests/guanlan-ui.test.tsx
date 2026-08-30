import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import "../src/i18n";
import {
  Badge,
  Button,
  Candles,
  Drawer,
  Inspector,
  MarketTicker,
  MetricCell,
  Panel,
  ResearchStep,
  Sparkline,
} from "../src/ui/guanlan";

describe("Guanlan port — Sparkline / Candles (方案 §25 无数据显形)", () => {
  it("renders a polyline for series data", () => {
    const { container } = render(<Sparkline data={[1, 3, 2, 5]} />);
    const poly = container.querySelector("polyline");
    expect(poly).toBeTruthy();
    expect(poly?.getAttribute("points")).toContain(",");
  });

  it("renders nothing when data is missing or too short (no fake chart)", () => {
    const { container: a } = render(<Sparkline data={[]} />);
    expect(a.querySelector("svg")).toBeNull();
    const { container: b } = render(<Sparkline data={[4]} />);
    expect(b.querySelector("svg")).toBeNull();
  });

  it("renders one candle body per datum; nothing on empty", () => {
    const data = [
      { o: 10, c: 12, h: 13, l: 9 },
      { o: 12, c: 11, h: 12.5, l: 10.5 },
    ];
    const { container } = render(<Candles data={data} />);
    expect(container.querySelectorAll("rect").length).toBe(2);
    const empty = render(<Candles data={[]} />);
    expect(empty.container.querySelector("svg")).toBeNull();
  });
});

describe("Guanlan port — MarketTicker / MetricCell (涨跌语义)", () => {
  it("marks negative delta as down and positive as up", () => {
    render(
      <MarketTicker
        items={[
          { name: "上证", value: "3952.18", delta: "+0.42%" },
          { name: "布油", value: "88.33", delta: "-1.10%" },
        ]}
      />,
    );
    expect(screen.getByText("+0.42%").className).toContain("up");
    expect(screen.getByText("-1.10%").className).toContain("down");
  });

  it("MetricCell renders unit and signed delta class", () => {
    render(<MetricCell label="总市值" value="1615" unit="亿" delta="-0.81%" />);
    expect(screen.getByText("总市值")).toBeTruthy();
    expect(screen.getByText("亿")).toBeTruthy();
    expect(screen.getByText("-0.81%").className).toContain("down");
  });
});

describe("Guanlan port — ResearchStep (三态墨痕)", () => {
  it("running state renders pulse ring; done/pending do not", () => {
    const { container, rerender } = render(
      <ResearchStep step="02" label="财务核对" status="running" time="3s" />,
    );
    expect(container.firstElementChild?.getAttribute("data-status")).toBe("running");
    expect(container.querySelector(".gl-step-marker-ring")).toBeTruthy();

    rerender(<ResearchStep step="02" label="财务核对" status="done" time="3s" />);
    expect(container.firstElementChild?.getAttribute("data-status")).toBe("done");
    expect(container.querySelector(".gl-step-marker-ring")).toBeNull();

    rerender(<ResearchStep step="02" label="财务核对" status="pending" />);
    expect(container.querySelector(".gl-step-marker-dot")).toBeTruthy();
    expect(container.querySelector(".gl-step-time")).toBeNull();
  });
});

describe("Guanlan port — Panel / Badge / Button / Inspector", () => {
  it("Panel renders header only when title or actions present", () => {
    const { container, rerender } = render(
      <Panel title="产业链" hint="SEGMENTS" actions={<Button>操作</Button>}>内容</Panel>,
    );
    expect(screen.getByText("产业链")).toBeTruthy();
    expect(screen.getByText("SEGMENTS")).toBeTruthy();
    expect(container.querySelector(".gl-panel-header")).toBeTruthy();

    rerender(<Panel>仅内容</Panel>);
    expect(container.querySelector(".gl-panel-header")).toBeNull();
  });

  it("Badge applies tone class", () => {
    render(<Badge tone="error">失败</Badge>);
    expect(screen.getByText("失败").className).toContain("gl-badge-error");
  });

  it("Button defaults to type=button and supports variant", () => {
    render(<Button variant="primary">运行</Button>);
    const btn = screen.getByText("运行") as HTMLButtonElement;
    expect(btn.type).toBe("button");
    expect(btn.className).toContain("gl-button-primary");
  });

  it("Inspector renders title and body", () => {
    render(<Inspector title="环节详情">分离冶炼</Inspector>);
    expect(screen.getByText("环节详情")).toBeTruthy();
    expect(screen.getByText("分离冶炼")).toBeTruthy();
  });
});

describe("Guanlan port — Drawer (交互)", () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  it("renders dialog when open, nothing when closed", () => {
    const { container } = render(<Drawer open={false} onClose={() => {}}>x</Drawer>);
    expect(container.querySelector(".gl-drawer")).toBeNull();

    render(<Drawer open onClose={() => {}} title="研究脉络">内容</Drawer>);
    expect(screen.getByRole("dialog")).toBeTruthy();
    expect(screen.getByText("研究脉络")).toBeTruthy();
  });

  it("Escape triggers onClose; scrim click triggers onClose", () => {
    const onClose = vi.fn();
    const { container } = render(<Drawer open onClose={onClose}>x</Drawer>);
    fireEvent.keyDown(window, { key: "Escape" });
    expect(onClose).toHaveBeenCalledTimes(1);
    fireEvent.click(container.querySelector(".gl-drawer-scrim")!);
    expect(onClose).toHaveBeenCalledTimes(2);
  });
});
