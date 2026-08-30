import { beforeEach, describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import i18n from "../src/i18n";
import { CommandCenterPage } from "../src/features/command-center/CommandCenterPage";
import { stepIndex, stepToInkStatus } from "../src/features/command-center/plan";
import { ResearchStep } from "../src/ui/guanlan";

describe("Command Center — plan step mapping (方案 §6 计划区)", () => {
  it("maps ASRO step statuses onto donor ink tri-state", () => {
    expect(stepToInkStatus("ok")).toBe("done");
    expect(stepToInkStatus("running")).toBe("running");
    expect(stepToInkStatus("pending")).toBe("pending");
    expect(stepToInkStatus("unknown-later-status")).toBe("pending");
  });

  it("formats zero-padded mono step indices", () => {
    expect(stepIndex(0)).toBe("01");
    expect(stepIndex(9)).toBe("10");
  });

  it("renders ink steps for the three statuses", () => {
    const { container, rerender } = render(
      <ResearchStep step="01" label="解析研究标的" status="done" />,
    );
    expect(container.firstElementChild?.getAttribute("data-status")).toBe("done");
    rerender(<ResearchStep step="02" label="运行完整研究管线" status="running" />);
    expect(container.firstElementChild?.getAttribute("data-status")).toBe("running");
  });
});

describe("Command Center — page shell (Guanlan Direct Port G1)", () => {
  beforeEach(async () => {
    window.localStorage.clear();
    Object.defineProperty(navigator, "language", {
      value: "zh-CN",
      configurable: true,
    });
    await i18n.changeLanguage("zh-CN");
  });

  it("renders the three-column workbench shell with localized header", { timeout: 15000 }, async () => {
    const client = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    render(
      <QueryClientProvider client={client}>
        <MemoryRouter initialEntries={["/"]}>
          <CommandCenterPage />
        </MemoryRouter>
      </QueryClientProvider>,
    );
    expect(await screen.findByText("研究总览")).toBeTruthy();
    expect(screen.getByTestId("commander-page")).toBeTruthy();
    expect(screen.getByTestId("commander-left")).toBeTruthy();
    expect(screen.getByTestId("commander-right")).toBeTruthy();
    expect(screen.getByTestId("commander-conversation")).toBeTruthy();
    // no raw i18n keys leak into the shell
    expect(document.body.textContent).not.toContain("cc.");
    expect(document.body.textContent).not.toContain("commander.");
  });
});
