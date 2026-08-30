import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { Panel } from "../../ui/guanlan";

/**
 * 版本比较（donor 版本对照习语 → ASRO 真实回测聚合，方案 §17）：
 * 同名策略的另一个版本 → 并排展示 回测聚合（组合平均收益/命中率/标的覆盖/
 * 裁决）。全部真实数据；无回测 → 显形 —（§25）。
 */

interface VersionSummary {
  version_id: string;
  name: string;
  version_no: number;
  status: string;
  verdict: string | null;
}

interface BacktestAggregate {
  portfolio_avg_return_pct?: number;
  portfolio_avg_hit_rate_pct?: number;
  instruments_backtested?: number;
  instruments_no_data?: number;
}

function useVersionDetail(versionId: string | null) {
  return useQuery({
    queryKey: ["strategy-compare", versionId],
    enabled: versionId != null && versionId !== "",
    queryFn: async () => {
      const resp = await fetch(`/api/v1/strategies/${versionId}`);
      if (!resp.ok) throw new Error("strategy.not_found");
      const body = (await resp.json()) as {
        strategy: {
          version_no: number;
          status: string;
          backtests: Array<{ aggregate: BacktestAggregate; status: string }>;
        };
      };
      return body.strategy;
    },
  });
}

function MetricRow({
  label,
  a,
  b,
}: {
  label: string;
  a: string | null;
  b: string | null;
}) {
  return (
    <li className="result-row">
      <span className="secondary">{label}</span>
      <span className="mono">{a ?? "—"}</span>
      <span className="mono">{b ?? "—"}</span>
    </li>
  );
}

function fmt(v: number | undefined, suffix = ""): string | null {
  if (v == null) return null;
  return `${v > 0 ? "+" : ""}${v}${suffix}`;
}

export function StrategyVersionCompare({
  current,
  siblings,
}: {
  current: { version_id: string; name: string; version_no: number; backtests: Array<{ aggregate: BacktestAggregate }> };
  siblings: VersionSummary[];
}) {
  const { t } = useTranslation();
  const sameName = useMemo(
    () => siblings.filter((s) => s.name === current.name && s.version_id !== current.version_id),
    [siblings, current.name, current.version_id],
  );
  const [otherId, setOtherId] = useState<string | null>(null);

  const otherQuery = useVersionDetail(sameName.length > 0 ? otherId : null);
  const other = otherQuery.data;
  const currentAgg = current.backtests[0]?.aggregate;
  const otherAgg = other?.backtests[0]?.aggregate;

  return (
    <Panel title={t("strategyWs.compareTitle")} hint={t("strategyWs.compareHint")}>
      {sameName.length === 0 ? (
        <p className="secondary">{t("strategyWs.compareNoSibling")}</p>
      ) : (
        <div data-testid="strategy-version-compare">
          <label className="ws-field">
            <span className="ws-field-label">{t("strategyWs.compareAgainst")}</span>
            <select
              className="control-input"
              value={otherId ?? ""}
              onChange={(e) => setOtherId(e.target.value || null)}
            >
              <option value="">—</option>
              {sameName.map((s) => (
                <option key={s.version_id} value={s.version_id}>
                  v{s.version_no} · {s.status}
                </option>
              ))}
            </select>
          </label>

          {otherId && (
            <ul className="watch-list sl-compare-table">
              <li className="result-row sl-compare-head">
                <span />
                <span className="mono">v{current.version_no}</span>
                <span className="mono">{other ? `v${other.version_no}` : ""}</span>
              </li>
              <MetricRow
                label={t("strategy.portfolioAvg")}
                a={fmt(currentAgg?.portfolio_avg_return_pct, "%")}
                b={fmt(otherAgg?.portfolio_avg_return_pct, "%")}
              />
              <MetricRow
                label={t("strategy.portfolioHit")}
                a={fmt(currentAgg?.portfolio_avg_hit_rate_pct, "%")}
                b={fmt(otherAgg?.portfolio_avg_hit_rate_pct, "%")}
              />
              <MetricRow
                label={t("strategy.instrumentsBacktested")}
                a={
                  currentAgg?.instruments_backtested != null
                    ? `${currentAgg.instruments_backtested}/${Number(currentAgg.instruments_backtested) + Number(currentAgg.instruments_no_data ?? 0)}`
                    : null
                }
                b={
                  otherAgg?.instruments_backtested != null
                    ? `${otherAgg.instruments_backtested}/${Number(otherAgg.instruments_backtested) + Number(otherAgg.instruments_no_data ?? 0)}`
                    : null
                }
              />
            </ul>
          )}
        </div>
      )}
    </Panel>
  );
}
