import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { Link, useSearchParams } from "react-router-dom";
import { InstrumentSearch } from "../components/InstrumentSearch";
import { ResearchPipelineCard } from "../components/ResearchPipelineCard";
import { formatTaskStatus, uiLang } from "../presentation/enumLabels";
import { formatWhen } from "../presentation/format";

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
  validation?: { instrument_return_pct: number };
}

interface ReportItem {
  report_id: string;
  instrument_id: string;
  created_at: string | null;
  latest_version_no: number;
}

function useInstrumentName(instrumentId: string | null) {
  const { data } = useQuery({
    queryKey: ["instrument", instrumentId],
    enabled: instrumentId != null,
    staleTime: 60000,
    queryFn: async (): Promise<{ name: string; code: string } | null> => {
      const resp = await fetch(`/api/v1/instruments/${encodeURIComponent(instrumentId ?? "")}`);
      if (!resp.ok) return null;
      const body = await resp.json();
      return body.instrument;
    },
  });
  return data;
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

/**
 * Home = Research Command Center (PW3 §19): search + live research, plus the
 * current research state at a glance — recent runs, active tasks, pending
 * predictions, latest reports. (Phase B of V2 总纲 will grow this into the
 * full AI 研究中枢; the layout keeps that direction.)
 */
export function HomePage() {
  const { t } = useTranslation();
  const [searchParams] = useSearchParams();
  const instrumentParam = searchParams.get("instrument");
  const autoRun = searchParams.get("run") === "1";
  const [selectedInstrument, setSelectedInstrument] = useState<string | null>(
    instrumentParam,
  );

  useEffect(() => {
    if (instrumentParam) setSelectedInstrument(instrumentParam);
  }, [instrumentParam]);

  const runsQuery = useQuery({
    queryKey: ["recent-runs"],
    queryFn: async (): Promise<RunItem[]> => {
      const resp = await fetch("/api/v1/research-runs?limit=6");
      if (!resp.ok) return [];
      const body = await resp.json();
      return body.results;
    },
    refetchInterval: 8000,
  });

  const tasksQuery = useQuery({
    queryKey: ["tasks"],
    queryFn: async (): Promise<TaskItem[]> => {
      const resp = await fetch("/api/v1/tasks");
      if (!resp.ok) return [];
      const body = await resp.json();
      return body.results;
    },
    refetchInterval: 8000,
  });

  const predsQuery = useQuery({
    queryKey: ["predictions-all"],
    queryFn: async (): Promise<PredictionItem[]> => {
      const resp = await fetch("/api/v1/predictions");
      if (!resp.ok) return [];
      const body = await resp.json();
      return body.results.filter((p: PredictionItem) => !p.validation).slice(0, 5);
    },
  });

  const reportsQuery = useQuery({
    queryKey: ["reports"],
    queryFn: async (): Promise<ReportItem[]> => {
      const resp = await fetch("/api/v1/reports");
      if (!resp.ok) return [];
      const body = await resp.json();
      return body.results.slice(0, 5);
    },
  });

  const activeTasks = (tasksQuery.data ?? []).filter((task) => task.status === "running");
  const duePreds = predsQuery.data ?? [];

  return (
    <main className="page">
      <h1>{t("home.title")}</h1>
      <p className="secondary">{t("home.description")}</p>

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

      <section className="card" data-testid="command-center">
        <h2>{t("commandCenter.title")}</h2>
        <div className="command-grid">
          <div className="command-cell">
            <h3>{t("commandCenter.recentResearch")}</h3>
            {(runsQuery.data ?? []).length === 0 && (
              <p className="secondary">{t("commandCenter.noResearchYet")}</p>
            )}
            <ul className="watch-list">
              {(runsQuery.data ?? []).map((run) => (
                <RunRow key={run.run_id} run={run} />
              ))}
            </ul>
          </div>

          <div className="command-cell">
            <h3>{t("commandCenter.activeTasks")}</h3>
            {activeTasks.length === 0 ? (
              <p className="secondary">
                {t("commandCenter.noActiveTasks", {
                  total: tasksQuery.data?.length ?? 0,
                })}
              </p>
            ) : (
              <ul className="watch-list">
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
          </div>

          <div className="command-cell">
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
          </div>

          <div className="command-cell">
            <h3>{t("commandCenter.recentReports")}</h3>
            {(reportsQuery.data ?? []).length === 0 && (
              <p className="secondary">{t("commandCenter.noReports")}</p>
            )}
            <ul className="watch-list">
              {(reportsQuery.data ?? []).map((r) => (
                <ReportRow key={r.report_id} report={r} />
              ))}
            </ul>
            <p>
              <Link to="/reports" className="secondary">
                {t("commandCenter.goReports")} →
              </Link>
            </p>
          </div>
        </div>
      </section>
    </main>
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

function ReportRow({ report }: { report: ReportItem }) {
  const { i18n } = useTranslation();
  const lang = uiLang(i18n.language);
  const profile = useInstrumentName(report.instrument_id);
  return (
    <li className="result-row">
      <Link to={`/reports/${report.report_id}`}>
        {profile?.name ?? report.instrument_id}
      </Link>
      <span className="secondary">v{report.latest_version_no}</span>
      <span className="secondary">{formatWhen(report.created_at, lang)}</span>
    </li>
  );
}
