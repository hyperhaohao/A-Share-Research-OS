import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { formatWhen, formatPct } from "../presentation/format";
import { uiLang } from "../presentation/enumLabels";

interface Monitor {
  monitor_id: string;
  version_id: string;
  name: string;
  universe: Array<{ instrument_id: string; name: string; rank: number }>;
  enabled: boolean;
  last_run_at: string | null;
  next_run_at: string | null;
}

interface Observation {
  observation_id: string;
  instrument_id: string;
  kind: string;
  text: string;
  observed_at: string | null;
}

interface Signal {
  signal_id: string;
  instrument_id: string;
  rule_kind: string;
  strength: number;
  text: string;
  observation_ids: string[];
}

interface Decision {
  decision_id: string;
  decision: string;
  confidence: number;
  rationale: string;
  observation_ids: string[];
  signal_ids: string[];
  as_of: string | null;
}

interface MonitorDetail {
  monitor: Monitor;
  observations: Observation[];
  signals: Signal[];
  decisions: Decision[];
}

export function StrategyMonitorsPage() {
  const { t, i18n } = useTranslation();
  const lang = uiLang(i18n.language);
  const { data, isPending, isError } = useQuery({
    queryKey: ["strategy-monitors"],
    queryFn: async (): Promise<Monitor[]> => {
      const resp = await fetch("/api/v1/strategy-monitors");
      if (!resp.ok) throw new Error("network.unreachable");
      const body = (await resp.json()) as { results: Monitor[] };
      return body.results;
    },
  });

  return (
    <main className="page" data-testid="monitors-page">
      <h1>{t("nav.monitoring")}</h1>
      <p className="secondary">{t("monitor.pageHint")}</p>
      {isPending && <p className="secondary">{t("common.loading")}</p>}
      {isError && <p className="status-error">{t("common.error")}</p>}
      {data && data.length === 0 && <p className="secondary">{t("monitor.empty")}</p>}
      {data && data.length > 0 && (
        <ul className="watch-list">
          {data.map((m) => (
            <li className="result-row" key={m.monitor_id} data-testid="monitor-row">
              <Link to={`/monitoring/${m.monitor_id}`} className="result-name">
                {m.name}
              </Link>
              <span className="secondary">
                {t("monitor.universeLabel", { count: m.universe.length })}
              </span>
              <span className="secondary">{formatWhen(m.last_run_at, lang)}</span>
            </li>
          ))}
        </ul>
      )}
    </main>
  );
}

const OBS_KIND_KEY: Record<string, string> = {
  quote_change: "monitor.obsQuote",
  corporate_event: "monitor.obsEvent",
  news: "monitor.obsNews",
};

export function StrategyMonitorDetailPage() {
  const params = useParams();
  const monitorId = params.monitorId ?? "";
  const { t, i18n } = useTranslation();
  const lang = uiLang(i18n.language);
  const queryClient = useQueryClient();

  const detailQuery = useQuery({
    queryKey: ["strategy-monitor", monitorId],
    enabled: monitorId !== "",
    refetchInterval: 5000,
    queryFn: async (): Promise<MonitorDetail> => {
      const resp = await fetch(`/api/v1/strategy-monitors/${monitorId}`);
      if (!resp.ok) throw new Error("monitor.not_found");
      return resp.json();
    },
  });

  const runM = useMutation({
    mutationFn: async () => {
      const resp = await fetch(`/api/v1/strategy-monitors/${monitorId}/run`, {
        method: "POST",
      });
      if (!resp.ok) {
        const err = (await resp.json().catch(() => null)) as { error_code?: string } | null;
        throw new Error(err?.error_code ?? "network.unreachable");
      }
      await resp.json();
      queryClient.invalidateQueries({ queryKey: ["strategy-monitor", monitorId] });
    },
  });

  if (detailQuery.isPending) {
    return (
      <main className="page" data-testid="monitor-detail">
        <p className="secondary">{t("common.loading")}</p>
      </main>
    );
  }
  if (detailQuery.isError || !detailQuery.data) {
    return (
      <main className="page" data-testid="monitor-detail">
        <p className="status-error">{t("common.error")}</p>
      </main>
    );
  }

  const { monitor, observations, signals, decisions } = detailQuery.data;
  const latest = decisions[0];

  return (
    <main className="page" data-testid="monitor-detail">
      <p>
        <Link to="/monitoring" className="secondary">
          ← {t("nav.monitoring")}
        </Link>
      </p>
      <div className="watch-card-head">
        <h1>{monitor.name}</h1>
        <span className={monitor.enabled ? "status-ok" : "secondary"}>
          {monitor.enabled ? t("monitor.active") : t("monitor.paused")}
        </span>
      </div>
      <p className="secondary">
        {t("monitor.universeLabel", { count: monitor.universe.length })} ·{" "}
        {t("monitor.lastRun", { when: formatWhen(monitor.last_run_at, lang) })} ·{" "}
        {t("monitor.nextRun", { when: formatWhen(monitor.next_run_at, lang) })}
      </p>

      <div className="header-controls" data-testid="monitor-actions">
        <button
          type="button"
          className="control-btn"
          data-testid="monitor-run"
          disabled={runM.isPending}
          onClick={() => runM.mutate()}
        >
          {t("monitor.runNow")}
        </button>
      </div>

      <section className="card" data-testid="monitor-observations">
        <h2>{t("monitor.observationsTitle")}</h2>
        {observations.length === 0 && <p className="secondary">{t("monitor.noRecords")}</p>}
        <ul className="watch-list">
          {observations.map((o) => (
            <li className="result-row" key={o.observation_id}>
              <span className="secondary">{t(OBS_KIND_KEY[o.kind] ?? o.kind)}</span>
              <span>{o.text}</span>
              <span className="secondary">{formatWhen(o.observed_at, lang)}</span>
            </li>
          ))}
        </ul>
      </section>

      <section className="card" data-testid="monitor-signals">
        <h2>{t("monitor.signalsTitle")}</h2>
        {signals.length === 0 && <p className="secondary">{t("monitor.noRecords")}</p>}
        <ul className="watch-list">
          {signals.map((s) => (
            <li className="result-row" key={s.signal_id}>
              <span className="secondary">{s.rule_kind}</span>
              <span>{s.text}</span>
              <span className="mono">{formatPct(s.strength)}</span>
            </li>
          ))}
        </ul>
      </section>

      <section className="card" data-testid="monitor-decisions">
        <h2>{t("monitor.decisionsTitle")}</h2>
        {decisions.length === 0 && <p className="secondary">{t("monitor.noRecords")}</p>}
        {latest && (
          <div className="task-grid">
            <span>{t("monitor.decisionLabel")}</span>
            <span>{t(`monitor.decision.${latest.decision}`)}</span>
            <span>{t("monitor.confidence")}</span>
            <span className="mono">{Math.round(latest.confidence * 100)}%</span>
            <span>{t("monitor.rationale")}</span>
            <span>{latest.rationale}</span>
            <span>{t("monitor.asOf")}</span>
            <span>{formatWhen(latest.as_of, lang)}</span>
          </div>
        )}
      </section>
    </main>
  );
}
