import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { Link, useSearchParams } from "react-router-dom";
import { InstrumentSearch } from "../components/InstrumentSearch";
import { ResearchPipelineCard } from "../components/ResearchPipelineCard";
import { ConversationPanel, useEnsureSession } from "../components/ConversationPanel";
import { ArtifactsPanel, PlanRow } from "../components/ArtifactsPanel";
import { CommandPlanSteps, type Plan } from "../components/CommandPlanSteps";
import { formatTaskStatus, uiLang } from "../presentation/enumLabels";
import { formatWhen } from "../presentation/format";
import { contextFromParams } from "../shared/context";
import { useInstrumentName } from "../shared/instrument";

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
 * Home = AI 研究中枢（V2 Phase B, 总纲 §38）：左 任务/计划、中 对话+执行、
 * 右 当前研究产物。直接驱动（搜索 + 实时管线）与对话驱动（计划）共用中栏。
 */
export function HomePage() {
  const { t } = useTranslation();
  const [searchParams] = useSearchParams();
  // V2 Phase A: deep links are decoded through the shared ResearchContext
  const ctx = contextFromParams(searchParams);
  const instrumentParam = ctx.primary_instrument_id;
  const autoRun = searchParams.get("run") === "1";
  const [selectedInstrument, setSelectedInstrument] = useState<string | null>(
    instrumentParam,
  );

  useEffect(() => {
    if (instrumentParam) setSelectedInstrument(instrumentParam);
  }, [instrumentParam]);

  const [sessionId] = useEnsureSession();

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
  const plans = ccQuery.data?.recent_plans ?? [];
  const activePlan =
    ccQuery.data?.current_plan ??
    (ccQuery.data?.recent_plans ?? [])[0] ??
    null;
  const runningRuns = ccQuery.data?.running_runs ?? [];
  const activeTasks = ccQuery.data?.active_tasks ?? [];
  const duePreds = (ccQuery.data?.pending_predictions ?? []).slice(0, 4);

  return (
    <main className="page layout-command" data-testid="commander-page">
      <h1>{t("home.title")}</h1>
      <p className="secondary">{t("home.description")}</p>

      <div className="commander-grid">
        <aside className="commander-col commander-left" data-testid="commander-left">
          <section className="card">
            <h3>{t("commander.currentPlan")}</h3>
            {activePlan ? (
              <CommandPlanSteps plan={activePlan} compact data-testid="commander-current-plan" />
            ) : (
              <p className="secondary">{t("commander.noPlanYet")}</p>
            )}
          </section>

          <section className="card">
            <h3>{t("commander.runningNow")}</h3>
            {runningRuns.length === 0 && activeTasks.length === 0 ? (
              <p className="secondary">{t("commandCenter.noResearchYet")}</p>
            ) : (
              <ul className="watch-list">
                {runningRuns.map((run) => (
                  <RunRow key={run.run_id} run={run} />
                ))}
                {activeTasks.map((task) => (
                  <TaskRow key={task.task_id} task={task} />
                ))}
              </ul>
            )}
            <p>
              <Link to="/tasks" className="secondary">
                {t("commandCenter.goTasks")} →
              </Link>
            </p>
          </section>

          <section className="card">
            <h3>{t("commander.recentPlans")}</h3>
            {plans.length === 0 && (
              <p className="secondary">{t("commandCenter.noResearchYet")}</p>
            )}
            <ul className="watch-list">
              {plans.map((plan) => (
                <PlanRow key={plan.plan_id} plan={plan} />
              ))}
            </ul>
          </section>
        </aside>

        <div className="commander-col commander-middle">
          <InstrumentSearch onSelect={(iid) => setSelectedInstrument(iid)} />

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

          <ConversationPanel
            sessionId={sessionId}
            activePlan={activePlan}
          />
        </div>

        <aside className="commander-col commander-right" data-testid="commander-right">
          <ArtifactsPanel activePlan={activePlan} />

          <section className="card">
            <h3>{t("commandCenter.pendingPredictions")}</h3>
            {duePreds.length === 0 ? (
              <p className="secondary">{t("commandCenter.noPredictions")}</p>
            ) : (
              <ul className="watch-list">
                {duePreds.map((p) => (
                  <PredRow key={p.prediction_id} prediction={p} />
                ))}
              </ul>
            )}
            <p>
              <Link to="/predictions" className="secondary">
                {t("commandCenter.goPredictions")} →
              </Link>
            </p>
          </section>
        </aside>
      </div>
    </main>
  );
}

function RunRow({ run }: { run: RunItem }) {
  const { t, i18n } = useTranslation();
  const lang = uiLang(i18n.language);
  const profile = useInstrumentName(run.instrument_id);
  return (
    <li className="result-row">
      <Link to={`/instrument/${run.instrument_id}`} className="result-name">
        {profile?.name ?? run.instrument_id}
      </Link>
      <span className="secondary">{formatWhen(run.started_at, lang)}</span>
      <span className={run.status === "failed" ? "status-error" : run.status === "succeeded" ? "status-ok" : "secondary"}>
        {t(`commandCenter.runStatus.${run.status}`, { defaultValue: run.status })}
      </span>
    </li>
  );
}

function TaskRow({ task }: { task: TaskItem }) {
  const { t, i18n } = useTranslation();
  const lang = uiLang(i18n.language);
  const profile = useInstrumentName(task.instrument_id);
  return (
    <li className="result-row">
      <Link to={`/instrument/${task.instrument_id}`}>{profile?.name ?? task.instrument_id}</Link>
      <span>{formatTaskStatus(task.status, lang)}</span>
      <Link to="/tasks" className="secondary">
        {t("commandCenter.viewTask")}
      </Link>
    </li>
  );
}

function PredRow({ prediction: p }: { prediction: PredictionItem }) {
  const { t, i18n } = useTranslation();
  const lang = uiLang(i18n.language);
  const profile = useInstrumentName(p.instrument_id);
  return (
    <li className="result-row">
      <Link to={`/instrument/${p.instrument_id}`}>{profile?.name ?? p.instrument_id}</Link>
      <span className="secondary">{t(`workspace.direction.${p.expected_direction}`)}</span>
      <span className="secondary">{t("predictions.dueBy", { date: formatWhen(p.due_at, lang) })}</span>
    </li>
  );
}
