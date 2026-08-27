import { beforeEach, describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import App from "../src/App";

describe("App smoke", () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  it("renders localized shell in zh-CN by default on zh system", async () => {
    Object.defineProperty(navigator, "language", {
      value: "zh-CN",
      configurable: true,
    });
    render(<App />);
    expect(await screen.findByText("研究总览")).toBeTruthy();
    expect(screen.getByText("界面语言")).toBeTruthy();
    expect(screen.getByText("外观")).toBeTruthy();
  });

  it("renders localized shell in en-US on en system", async () => {
    Object.defineProperty(navigator, "language", {
      value: "en-US",
      configurable: true,
    });
    const { unmount } = render(<App />);
    expect(await screen.findByText("Dashboard")).toBeTruthy();
    unmount();
  });

  it("exposes up/down samples with token-driven classes", async () => {
    render(<App />);
    const up = await screen.findByTestId("up-sample");
    const down = await screen.findByTestId("down-sample");
    expect(up.className).toContain("quote-up");
    expect(down.className).toContain("quote-down");
  });
});
