import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { useSearchParams } from "react-router-dom";
import { InstrumentSearch } from "../../components/InstrumentSearch";
import { ResearchPipelineCard } from "../../components/ResearchPipelineCard";
import { contextFromParams } from "../../shared/context";
import { CommandCenterLeft } from "./CommandCenterLeft";
import { CommandCenterTranscript } from "./CommandCenterTranscript";
import { CommandCenterWorkbench } from "./CommandCenterWorkbench";
import type { Plan } from "./plan";

interface RunItem {
  run_id: string;
  instrument_id: string;
  status: string;
  started_at: string | null;
}

interface TaskItem {
  task_id: string;
  instrument_id: string;
  status: string;
}

interface PredictionItem {
  prediction_id: string;
  instrument_id: string;
  horizon: string;
  expected_direction: string;
  due_at: string;
  confidence?: number;
  consistency?: string;
  instrument?: { name: string | null; code: string } | null;
}

interface CommandCenterView {
  running_runs: RunItem[];
  recent_runs: RunItem[];
  active_tasks: TaskItem[];
  current_plan: Plan | null;
  recent_plans: Plan[];
  pending_predictions: PredictionItem[];
  names: Record<string, { name: string | null; code: string }>;
  generated_at: string;
}

/**
 * AI 研究中枢（Guanlan Direct Port G1，方案 §6/§32）：donor 三栏工作台，
 * 数据全部来自 ASRO（/views/command-center + command sessions + artifacts）。
 * 左 计划墨痕 / 中 对话+执行链 / 右 真实当前 Workbench。
 */
export function CommandCenterPage() {
  const { t } = useTranslation();
  const [searchParams, setSearchParams] = useSearchParams();
  // V2 Phase A: deep links are decoded through the shared ResearchContext
  const ctx = contextFromParams(searchParams);
  const instrumentParam = ctx.primary_instrument_id;
  const autoRun = searchParams.get("run") === "1";
  const [selectedInstrument, setSelectedInstrument] = useState<string | null>(
    instrumentParam,
  );
  const [sessionId, setSessionId] = useState<string | null>(null);

  useEffect(() => {
    if (instrumentParam) setSelectedInstrument(instrumentParam);
  }, [instrumentParam]);

  // UX Foundation §10/§53: 首屏单请求聚合（请求预算 <= 3）
  const ccQuery = useQuery({
    queryKey: ["command-center-view"],
    queryFn: async (): Promise<CommandCenterView> => {
      const resp = await fetch("/api/v1/views/command-center");
      if (!resp.ok) throw new Error("network.unreachable");
      const body = await resp.json();
      return body.view;
    },
    refetchInterval: 5000,
  });

  // 会话自举：取最近会话，没有则创建（useEnsureSession 的可控版本，
  // 支持 donor 多会话切换行为）
  useBootstrapSession(sessionId, setSessionId);

  const plans = ccQuery.data?.recent_plans ?? [];
  const activePlan =
    ccQuery.data?.current_plan ?? (ccQuery.data?.recent_plans ?? [])[0] ?? null;
  const runningRuns = ccQuery.data?.running_runs ?? [];
  const activeTasks = ccQuery.data?.active_tasks ?? [];
  const duePreds = (ccQuery.data?.pending_predictions ?? []).slice(0, 4);
  const contextInstrument = activePlan?.instrument_id ?? selectedInstrument ?? null;

  return (
    <main className="page layout-command cc-page" data-testid="commander-page">
      <div className="cc-header">
        <h1>{t("home.title")}</h1>
        <p className="secondary">{t("home.description")}</p>
      </div>

      <div className="commander-grid cc-grid">
        <aside className="commander-col commander-left" data-testid="commander-left">
          <CommandCenterLeft
            activePlan={activePlan}
            plans={plans}
            runningRuns={runningRuns}
            activeTasks={activeTasks}
            sessionId={sessionId}
            onSessionChange={(id) => setSessionId(id)}
          />
        </aside>

        <div className="commander-col commander-middle">
          <InstrumentSearch
            onSelect={(iid) => {
              setSelectedInstrument(iid);
              void setSearchParams(
                (prev) => {
                  const next = new URLSearchParams(prev);
                  next.set("context", encodeURIComponent(iid));
                  return next;
                },
                { replace: true },
              );
            }}
          />

          {selectedInstrument && (
            <ResearchPipelineCard
              key={selectedInstrument}
              instrumentId={selectedInstrument}
              autoStart={autoRun}
            />
          )}
          {!selectedInstrument && (
            <section className="card">
              <p className="secondary">{t("home.searchPrompt")}</p>
            </section>
          )}

          <CommandCenterTranscript
            sessionId={sessionId}
            activePlan={activePlan}
            contextInstrument={contextInstrument}
          />
        </div>

        <aside className="commander-col commander-right" data-testid="commander-right">
          <CommandCenterWorkbench
            activePlan={activePlan}
            selectedInstrument={selectedInstrument}
            pendingPredictions={duePreds}
          />
        </aside>
      </div>
    </main>
  );
}

/** 最近会话自举（无会话则创建）；仅在未选中会话时生效一次。 */
function useBootstrapSession(
  sessionId: string | null,
  setSessionId: (id: string) => void,
) {
  useEffect(() => {
    if (sessionId != null) return;
    let cancelled = false;
    const boot = async () => {
      try {
        const resp = await fetch("/api/v1/command/sessions?limit=1");
        if (resp.ok) {
          const body = (await resp.json()) as {
            results: Array<{ session_id: string }>;
          };
          if (body.results.length > 0 && !cancelled) {
            setSessionId(body.results[0].session_id);
            return;
          }
        }
        const created = await fetch("/api/v1/command/sessions", { method: "POST" });
        if (!created.ok) return;
        const body = (await created.json()) as {
          session: { session_id: string };
        };
        if (!cancelled) setSessionId(body.session.session_id);
      } catch {
        /* offline: leave null; the composer stays disabled via enabled gates */
      }
    };
    void boot();
    return () => {
      cancelled = true;
    };
  }, [sessionId, setSessionId]);
}
