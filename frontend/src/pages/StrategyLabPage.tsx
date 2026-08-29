import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { uiLang } from "../presentation/enumLabels";
import { artifactByDomain, handoffPath, recordHandoff } from "../shared/handoff";
import { newResearchContext } from "../shared/context";
import { formatWhen } from "../presentation/format";

interface BacktestResult {
  instrument_id: string;
  name: string | null;
  status: string;
  samples?: number;
  hit_rate_pct?: number;
  avg_return_pct?: number;
  window?: string;
  error?: string;
}

interface Backtest {
  backtest_id: string;
  status: string;
  results: BacktestResult[];
  aggregate: Record<string, unknown>;
  failure_cases: Array<Record<string, unknown>>;
  error: string | null;
  created_at: string | null;
}

interface StrategyVersion {
  version_id: string;
  name: string;
  version_no: number;
  philosophy: string;
  status: string;
  verdict: string | null;
  universe: Array<{ instrument_id: string; code: string; name: string; rank: number }>;
  entry_policy: Record<string, unknown>;
  backtests: Backtest[];
  created_at: string | null;
  updated_at: string | null;
}

export function StrategyLabPage() {
  const { t, i18n } = useTranslation();
  const lang = uiLang(i18n.language);
  const { data, isPending, isError } = useQuery({
    queryKey: ["strategies"],
    queryFn: async (): Promise<StrategyVersion[]> => {
      const resp = await fetch("/api/v1/strategies");
      if (!resp.ok) throw new Error("network.unreachable");
      const body = (await resp.json()) as { results: StrategyVersion[] };
      return body.results;
    },
  });

  return (
    <main className="page" data-testid="strategy-page">
      <h1>{t("nav.strategy")}</h1>
      <p className="secondary">{t("strategy.pageHint")}</p>
      {isPending && <p className="secondary">{t("common.loading")}</p>}
      {isError && <p className="status-error">{t("common.error")}</p>}
      {data && data.length === 0 && <p className="secondary">{t("strategy.empty")}</p>}
      {data && data.length > 0 && (
        <ul className="watch-list">
          {data.map((s) => (
            <li className="result-row" key={s.version_id} data-testid="strategy-row">
              <Link to={`/strategy/${s.version_id}`} className="result-name">
                {s.name} · v{s.version_no}
              </Link>
              <span className={s.status === "EXPERIMENTAL" ? "status-ok" : "secondary"}>
                {t(`strategy.status.${s.status}`)}
              </span>
              <span className="secondary">{formatWhen(s.created_at, lang)}</span>
            </li>
          ))}
        </ul>
      )}
    </main>
  );
}

function BacktestBlock({ backtest }: { backtest: Backtest }) {
  const { t } = useTranslation();
  const agg = backtest.aggregate as Record<string, number | string | undefined>;
  return (
    <section className="card" data-testid="backtest-block">
      <div className="watch-card-head">
        <h2>{t("strategy.backtestTitle")}</h2>
        <span
          className={
            backtest.status === "failed"
              ? "status-error"
              : backtest.status === "completed"
                ? "status-ok"
                : "secondary"
          }
        >
          {t(`workflow.status.${backtest.status}`)}
        </span>
      </div>
      {backtest.status === "failed" && <p className="status-error">{backtest.error}</p>}
      {backtest.status === "completed" && (
        <>
          <div className="task-grid">
            <span>{t("strategy.portfolioAvg")}</span>
            <span className="mono">{String(agg.portfolio_avg_return_pct)}%</span>
            <span>{t("strategy.portfolioHit")}</span>
            <span className="mono">{String(agg.portfolio_avg_hit_rate_pct)}%</span>
            <span>{t("strategy.instrumentsBacktested")}</span>
            <span className="mono">
              {String(agg.instruments_backtested)} /{" "}
              {Number(agg.instruments_backtested) + Number(agg.instruments_no_data)}
            </span>
          </div>
          {backtest.failure_cases.length > 0 && (
            <div data-testid="failure-cases">
              <h3>{t("strategy.failureCases")}</h3>
              <ul className="watch-list">
                {backtest.failure_cases.map((f) => (
                  <li className="result-row" key={String(f.instrument_id)}>
                    <span className="status-error">✗ {String(f.name)}</span>
                    <span className="mono">{String(f.avg_return_pct)}%</span>
                    <span className="secondary">{String(f.reason)}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
          <ul className="watch-list">
            {backtest.results.map((r) => (
              <li className="result-row" key={r.instrument_id}>
                <span>{r.name ?? r.instrument_id}</span>
                {r.status === "ok" ? (
                  <span className="mono">
                    {r.avg_return_pct}% · {r.hit_rate_pct}% · {r.samples}
                  </span>
                ) : (
                  <span className="secondary">
                    {t(`strategy.resultStatus.${r.status}`)}
                  </span>
                )}
              </li>
            ))}
          </ul>
        </>
      )}
      {backtest.status === "running" && <p className="secondary">{t("workflow.running")}</p>}
    </section>
  );
}

export function StrategyDetailPage() {
  const params = useParams();
  const versionId = params.versionId ?? "";
  const { t, i18n } = useTranslation();
  const lang = uiLang(i18n.language);
  const queryClient = useQueryClient();
  const [latestBacktestId, setLatestBacktestId] = useState<string | null>(null);

  const detailQuery = useQuery({
    queryKey: ["strategy", versionId],
    enabled: versionId !== "",
    refetchInterval: 6000,
    queryFn: async (): Promise<StrategyVersion> => {
      const resp = await fetch(`/api/v1/strategies/${versionId}`);
      if (!resp.ok) throw new Error("strategy.not_found");
      const body = (await resp.json()) as { strategy: StrategyVersion };
      return body.strategy;
    },
  });

  const backtestQuery = useQuery({
    queryKey: ["strategy-backtest", latestBacktestId],
    enabled: latestBacktestId != null,
    refetchInterval: 1500,
    queryFn: async (): Promise<Backtest> => {
      const resp = await fetch(`/api/v1/strategies/backtests/${latestBacktestId}`);
      if (!resp.ok) throw new Error("strategy.not_found");
      const body = (await resp.json()) as { backtest: Backtest };
      return body.backtest;
    },
  });

  const invalidate = () =>
    queryClient.invalidateQueries({ queryKey: ["strategy", versionId] });

  const backtestM = useMutation({
    mutationFn: async () => {
      const resp = await fetch(`/api/v1/strategies/${versionId}/backtest`, {
        method: "POST",
      });
      if (!resp.ok) {
        const err = (await resp.json().catch(() => null)) as { error_code?: string } | null;
        throw new Error(err?.error_code ?? "network.unreachable");
      }
      const body = (await resp.json()) as { backtest: Backtest };
      setLatestBacktestId(body.backtest.backtest_id);
      return body.backtest;
    },
  });
  const monitorM = useMutation({
    mutationFn: async () => {
      const resp = await fetch("/api/v1/strategy-monitors", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ version_id: versionId }),
      });
      if (!resp.ok) {
        const err = (await resp.json().catch(() => null)) as { error_code?: string } | null;
        throw new Error(err?.error_code ?? "network.unreachable");
      }
      const body = (await resp.json()) as { monitor: { monitor_id: string } };
      // §2/红线 5: the cross-module action carries a handoff envelope
      const strategyArtifact = await artifactByDomain("StrategyVersion", versionId);
      if (strategyArtifact != null) {
        const envelope = await recordHandoff({
          source_module: "strategy",
          target_module: "monitor",
          action: "create_monitor",
          artifact_ids: [strategyArtifact.artifact_id],
          context: newResearchContext({}),
          message: "strategy → create_monitor",
        });
        return handoffPath(`/monitoring/${body.monitor.monitor_id}`, envelope);
      }
      return `/monitoring/${body.monitor.monitor_id}`;
    },
    onSuccess: (monitorId: string) => {
      window.location.assign(`/monitoring/${monitorId}`);
    },
  });
  const validateM = useMutation({
    mutationFn: async () => {
      const resp = await fetch(`/api/v1/strategies/${versionId}/validate`, {
        method: "POST",
      });
      if (!resp.ok) {
        const err = (await resp.json().catch(() => null)) as { error_code?: string } | null;
        throw new Error(err?.error_code ?? "network.unreachable");
      }
      await resp.json();
      invalidate();
    },
  });

  const strategy = detailQuery.data;
  const shownBacktest = latestBacktestId
    ? backtestQuery.data ?? null
    : strategy?.backtests[0] ?? null;
  const gateError =
    monitorM.error instanceof Error
      ? monitorM.error.message
      : backtestM.error instanceof Error
        ? backtestM.error.message
        : validateM.error instanceof Error
          ? validateM.error.message
          : null;

  if (detailQuery.isPending) {
    return (
      <main className="page" data-testid="strategy-detail">
        <p className="secondary">{t("common.loading")}</p>
      </main>
    );
  }
  if (detailQuery.isError || !strategy) {
    return (
      <main className="page" data-testid="strategy-detail">
        <p className="status-error">{t("common.error")}</p>
      </main>
    );
  }

  return (
    <main className="page" data-testid="strategy-detail">
      <p>
        <Link to="/strategy" className="secondary">
          ← {t("nav.strategy")}
        </Link>
      </p>
      <div className="watch-card-head">
        <h1>
          {strategy.name} · v{strategy.version_no}
        </h1>
        <span className={strategy.status === "EXPERIMENTAL" ? "status-ok" : "secondary"}>
          {t(`strategy.status.${strategy.status}`)}
        </span>
      </div>
      <section className="card">
        <h2>{t("strategy.philosophy")}</h2>
        <p>{strategy.philosophy}</p>
        <div className="task-grid">
          <span>{t("strategy.universeSize")}</span>
          <span className="mono">{strategy.universe.length}</span>
          <span>{t("strategy.entryPolicy")}</span>
          <span className="mono">
            {t("strategy.forwardReturn", {
              horizon: String(strategy.entry_policy.horizon_days ?? ""),
            })}
          </span>
        </div>
      </section>

      {strategy.verdict && (
        <p className="status-ok" data-testid="strategy-verdict">
          {strategy.verdict}
        </p>
      )}

      <div className="header-controls" data-testid="strategy-actions">
        <button
          type="button"
          className="control-btn"
          data-testid="monitor-create"
          disabled={monitorM.isPending}
          onClick={() => monitorM.mutate()}
        >
          {t("monitor.create")}
        </button>
        <button
          type="button"
          className="control-btn"
          data-testid="strategy-backtest"
          disabled={backtestM.isPending}
          onClick={() => backtestM.mutate()}
        >
          {t("strategy.runBacktest")}
        </button>
        <button
          type="button"
          className="control-btn"
          data-testid="strategy-validate"
          disabled={validateM.isPending}
          onClick={() => validateM.mutate()}
        >
          {t("strategy.validate")}
        </button>
        {gateError && (
          <span className="status-error">
            {t(`errors.${gateError}`, { defaultValue: t("common.error") })}
          </span>
        )}
      </div>

      {shownBacktest && <BacktestBlock backtest={shownBacktest} />}
      <p className="secondary">
        {t("strategy.updated", {
          when: formatWhen(strategy.updated_at ?? strategy.created_at, lang),
        })}
      </p>
    </main>
  );
}
