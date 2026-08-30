import { useTranslation } from "react-i18next";
import { Panel } from "../../ui/guanlan";
import type { ExperienceCardDetail } from "./experienceView";

/**
 * 炼（donor RefinePane → ASRO 卡字段，方案 §14）：
 * 经验陈述 / 机制 / 适用与失效条件 / 量化表达式。真实卡内容，不做 CRUD 表单。
 */
export function ExperienceRefinePane({ card }: { card: ExperienceCardDetail }) {
  const { t } = useTranslation();
  return (
    <div className="ew-pane">
      <Panel title={t("experienceWs.refineTitle")} hint={`v${card.current_version} · ${t(`experience.method.${card.refine_method}`)}`}>
        <section className="ew-refine-section">
          <h4 className="ew-refine-label">{t("experienceWs.statementTitle")}</h4>
          <p className="ew-refine-text serif">{card.statement}</p>
        </section>
        <section className="ew-refine-section">
          <h4 className="ew-refine-label">{t("experienceWs.mechanismTitle")}</h4>
          <p className="ew-refine-text">{card.mechanism || "—"}</p>
        </section>
        <div className="ew-cond-grid">
          <section className="ew-refine-section">
            <h4 className="ew-refine-label">{t("experienceWs.applicableTitle")}</h4>
            {card.applicable_conditions.length === 0 ? (
              <p className="secondary">—</p>
            ) : (
              <ul className="ew-cond-list">
                {card.applicable_conditions.map((c, i) => (
                  <li key={i}>{c}</li>
                ))}
              </ul>
            )}
          </section>
          <section className="ew-refine-section">
            <h4 className="ew-refine-label">{t("experienceWs.invalidTitle")}</h4>
            {card.invalid_conditions.length === 0 ? (
              <p className="secondary">—</p>
            ) : (
              <ul className="ew-cond-list ew-cond-invalid">
                {card.invalid_conditions.map((c, i) => (
                  <li key={i}>{c}</li>
                ))}
              </ul>
            )}
          </section>
        </div>
        <section className="ew-refine-section">
          <h4 className="ew-refine-label">{t("experienceWs.expressionTitle")}</h4>
          {card.quant_expression ? (
            <code className="ew-expr mono">{card.quant_expression}</code>
          ) : (
            <p className="secondary">{t("experienceWs.noExpression")}</p>
          )}
        </section>
      </Panel>
    </div>
  );
}
