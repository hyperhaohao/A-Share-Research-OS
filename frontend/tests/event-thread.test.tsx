import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import i18n from "../src/i18n";
import { EventThread, type CommandEvent } from "../src/features/command-center/EventThread";

function makeEvent(overrides: Partial<CommandEvent>): CommandEvent {
  return {
    event_id: "evt_" + Math.random().toString(16).slice(2),
    session_id: "ses_x",
    sequence: 1,
    event_type: "tool_call",
    created_at: "2026-09-02T00:00:00+00:00",
    correlation_id: null,
    plan_id: null,
    task_id: null,
    status: null,
    payload: {},
    artifact_ids: [],
    provenance: {},
    ...overrides,
  };
}

function renderThread(sessionId = "ses_x") {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <EventThread sessionId={sessionId} />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("Command Center — Event Thread cards (F10, 任务书 §8.10)", () => {
  beforeEach(async () => {
    window.localStorage.clear();
    await i18n.changeLanguage("zh-CN");
  });

  it("renders tool call/result/error/task/confirmation cards from the event stream", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        const url = String(input);
        if (url.includes("/events")) {
          const results: CommandEvent[] = [
            makeEvent({ event_type: "tool_call", sequence: 1, status: "running",
                        payload: { tool: "search_evidence", schema_version: "v1" } }),
            makeEvent({ event_type: "tool_result", sequence: 2, status: "completed",
                        payload: { tool: "search_evidence", detail: "50 条证据" },
                        artifact_ids: ["art_1"] }),
            makeEvent({ event_type: "tool_error", sequence: 3, status: "failed",
                        payload: { tool: "run_screening", error: "card missing" } }),
            makeEvent({ event_type: "task_completed", sequence: 4, task_id: "bgt_1",
                        status: "succeeded",
                        payload: { tool: "build_pit_snapshot", progress: 100 } }),
            makeEvent({ event_type: "run_failed", sequence: 5, status: "failed",
                        payload: { failed_step: "运行研究管线" } }),
          ];
          return new Response(JSON.stringify({ results, latest_sequence: 5 }), {
            status: 200,
          });
        }
        return new Response("{}", { status: 200 });
      }),
    );

    renderThread();
    await waitFor(() => {
      expect(screen.getByTestId("card-tool-call")).toBeTruthy();
      expect(screen.getByTestId("card-tool-result")).toBeTruthy();
      expect(screen.getByTestId("card-tool-error")).toBeTruthy();
      expect(screen.getByTestId("card-task-succeeded")).toBeTruthy();
      expect(screen.getByTestId("card-run-failed")).toBeTruthy();
    });
    // 失败显形：错误文本可见
    expect(screen.getByText(/card missing/)).toBeTruthy();
    vi.unstubAllGlobals();
  });

  it("confirmation card approve action creates and approves a server confirmation", async () => {
    const calls: Array<{ url: string; method: string; body?: unknown }> = [];
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        const url = String(input);
        const method = init?.method ?? "GET";
        calls.push({ url, method, body: init?.body });
        if (url.includes("/events")) {
          const results: CommandEvent[] = [
            makeEvent({
              event_type: "confirmation_requested",
              sequence: 1,
              status: "pending",
              correlation_id: "cfm_x",
              payload: { tool: "submit_thesis_revision",
                         arguments_digest: "d1e2e3",
                         arguments: { instrument_id: "SZSE:000831" } },
            }),
          ];
          return new Response(JSON.stringify({ results, latest_sequence: 1 }), { status: 200 });
        }
        if (url.endsWith("/confirmations") && method === "POST") {
          return new Response(
            JSON.stringify({ confirmation: { confirmation_id: "cfm_new" } }),
            { status: 201 },
          );
        }
        if (url.endsWith("/decide") && method === "POST") {
          return new Response(
            JSON.stringify({ confirmation: { status: "approved" } }),
            { status: 200 },
          );
        }
        return new Response("{}", { status: 200 });
      }),
    );

    renderThread();
    const approve = await screen.findByTestId("confirmation-approve");
    fireEvent.click(approve);
    await waitFor(() => {
      const decide = calls.find((c) => c.url.endsWith("/decide"));
      expect(decide).toBeTruthy();
      expect((decide!.body as string)).toContain("approved");
    });
    vi.unstubAllGlobals();
  });
});
