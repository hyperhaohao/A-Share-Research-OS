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
    // nav link + h1 both say Dashboard; scope to the heading
    const headings = await screen.findAllByRole("heading", { name: "Dashboard" });
    expect(headings.length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("Appearance")).toBeTruthy();
    unmount();
  });

});
