import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { Badge, Panel } from "../../ui/guanlan";

/**
 * 策略配方（Guanlan Direct Port G6，方案 §17 物料装配 → ASRO §46 组装现实）：
 * 策略由 物料 组装 —— 来源筛选运行（股票池）+ 来源经验卡（理念）+ 入场/出场/
 * 风险政策。全部真实溯源链接（Provenance 可点）。
 */

interface Composition {
  source_screening_run_id: string | null;
  source_card_id: string | null;
  universe: Array<{ instrument_id: string; code: string; name: string; rank: number }>;
  entry_policy: Record<string, unknown>;
  exit_policy: Record<string, unknown>;
  risk_policy: Record<string, unknown>;
}

export function StrategyCompositionPanel({ composition }: { composition: Composition }) {
  const { t } = useTranslation();
  const entry = composition.entry_policy ?? {};
  const exit = composition.exit_policy ?? {};
  const risk = composition.risk_policy ?? {};
  return (
    <Panel title={t("strategyWs.compositionTitle")} hint={t("strategyWs.compositionHint")}>
      <div className="sl-materials" data-testid="strategy-composition">
        <div className="sl-material-row">
          <span className="ew-refine-label">{t("strategyWs.materialPool")}</span>
          <div className="sl-material-chips">
            {composition.source_screening_run_id && (
              <Link
    className="sl-material-chip sl-material-screening"
                to={`/screening/${composition.source_screening_run_id}`}
              >
                {t("strategyWs.materialScreening")} →
              </Link>
            )}
            {composition.source_card_id && (
              <Link
                className="sl-material-chip sl-material-card"
                to={`/experience/${composition.source_card_id}`}
              >
                {t("strategyWs.materialCard")} →
              </Link>
            )}
            {!composition.source_screening_run_id && !composition.source_card_id && (
              <span className="secondary">—</span>
            )}
          </div>
        </div>

        <div className="sl-material-row">
          <span className="ew-refine-label">{t("strategyWs.policies")}</span>
          <div className="sl-policy-grid">
            <div className="cc-brief-cell">
              <div className="cc-brief-label">{t("strategy.entryPolicy")}</div>
              <div className="mono">
                {t("strategy.forwardReturn", { horizon: String(entry.horizon_days ?? "") })}
                {entry.threshold_pct != null ? ` / ${String(entry.threshold_pct)}%` : ""}
              </div>
            </div>
            <div className="cc-brief-cell">
              <div className="cc-brief-label">{t("strategyWs.exitPolicy")}</div>
              <div className="mono">{String(exit.kind ?? "—")}</div>
            </div>
            <div className="cc-brief-cell">
              <div className="cc-brief-label">{t("strategyWs.riskPolicy")}</div>
              <div className="mono">{String(risk.kind ?? "—")}</div>
            </div>
          </div>
        </div>

        <div className="sl-material-row">
          <span className="ew-refine-label">
            {t("strategyWs.universeChips", { count: composition.universe.length })}
          </span>
          <div className="sl-universe-chips">
            {composition.universe.slice(0, 8).map((u) => (
              <Link key={u.instrument_id} className="sl-universe-chip" to={`/instrument/${u.instrument_id}`}>
                <span className="mono">#{u.rank}</span> {u.name}
              </Link>
            ))}
            {composition.universe.length > 8 && (
              <Badge tone="neutral">+{composition.universe.length - 8}</Badge>
            )}
            {composition.universe.length === 0 && <span className="secondary">—</span>}
          </div>
        </div>
      </div>
    </Panel>
  );
}
