import { useTranslation } from "react-i18next";
import { Panel } from "../../ui/guanlan";
import { uiLang } from "../../presentation/enumLabels";
import { formatWhen } from "../../presentation/format";
import type { IndustryView } from "./industryView";

const AXIS_NAME_KEYS: Record<string, string> = {
  global_demand: "industryWs.axis.global_demand",
  pricing_cycle: "industryWs.axis.pricing_cycle",
  domestic_substitution: "industryWs.axis.domestic_substitution",
  technology_route: "industryWs.axis.technology_route",
  theme_mapping: "industryWs.axis.theme_mapping",
};
const AXIS_GLOSS_KEYS: Record<string, string> = {
  global_demand: "industryWs.axisGloss.global_demand",
  pricing_cycle: "industryWs.axisGloss.pricing_cycle",
  domestic_substitution: "industryWs.axisGloss.domestic_substitution",
  technology_route: "industryWs.axisGloss.technology_route",
  theme_mapping: "industryWs.axisGloss.theme_mapping",
};

/**
 * 全球产业坐标（donor 全球坐标 → ASRO 真实主题/指标，方案 §10/§12）。
 * 五条逻辑轴 β/Δ/Ω/Θ/Ψ 保留；轴下环节站位（领先/并跑/追赶/短板）尚无
 * 证据源 → 「暂无定位」显形；真实宏观主题与指标随视图披露。
 * 与全球宏观（G8）分离：本视图只回答「该产业在全球竞争中的位置」。
 */
export function GlobalIndustryPositionView({ view }: { view: IndustryView }) {
  const { t, i18n } = useTranslation();
  const lang = uiLang(i18n.language);
  return (
    <div className="ir-matrix">
      <div className="ir-matrix-head">
        <span className="ir-matrix-title">{t("industryWs.matrixTitle")}</span>
        <span className="secondary">{t("industryWs.matrixHint")}</span>
      </div>

      <p className="secondary ir-disclosure" data-testid="global-context-disclosure">
        {view.global.disclosures.note ?? t("industryWs.noDisclosure")}
      </p>

      <div className="ir-axes">
        {view.global.axes.map((axis) => (
          <div key={axis.key} className="ir-axis-lane" data-testid="industry-axis-lane">
            <div className="ir-axis-label">
              <span className="ir-axis-greek serif">{axis.greek}</span>
              <div>
                <div className="ir-axis-name">{t(AXIS_NAME_KEYS[axis.key])}</div>
                <div className="secondary mono cc-brief-code">{t(AXIS_GLOSS_KEYS[axis.key])}</div>
              </div>
            </div>
            <div className="ir-axis-items">
              <span className="secondary" data-testid="industry-position-empty">
                {t("industryWs.noPositions")}
              </span>
            </div>
          </div>
        ))}
      </div>

      <div className="ir-matrix-panels">
        <Panel title={t("industryWs.themes")} hint={t("industryWs.themesHint")}>
          {view.global.themes.length === 0 ? (
            <p className="secondary">{t("industryWs.noThemes")}</p>
          ) : (
            <ul className="watch-list" data-testid="industry-themes">
              {view.global.themes.map((th) => (
                <li key={th.evidence_id} className="result-row ir-theme-row">
                  <span className="ir-theme-title">{th.summary.slice(0, 60)}
                    {th.summary.length > 60 ? "…" : ""}</span>
                  <span className="secondary mono">
                    {formatWhen(th.available_time, lang)}
                    {th.mentions_official_body ? ` · ${t("industryWs.officialMention")}` : ""}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </Panel>

        <Panel title={t("industryWs.indicators")} hint={t("industryWs.indicatorsHint")}>
          {view.global.indicators.length === 0 ? (
            <p className="secondary">{t("industryWs.noIndicators")}</p>
          ) : (
            <div className="ir-indicator-grid" data-testid="global-indicators">
              {view.global.indicators.map((ind) => (
                <div key={ind.code} className="cc-brief-cell">
                  <div className="cc-brief-label">{ind.name}</div>
                  <div className="num">
                    {ind.value == null ? "—" : ind.value.toLocaleString()}
                    {ind.change != null && (
                      <span
                        className={
                          ind.change >= 0 ? "up pct-up ir-ind-chg" : "down pct-down ir-ind-chg"
                        }
                      >
                        {" "}
                        {ind.change >= 0 ? "+" : ""}
                        {ind.change.toFixed(2)}%
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </Panel>
      </div>

      <p className="secondary ir-reading">{t("industryWs.readingGuide")}</p>
    </div>
  );
}
